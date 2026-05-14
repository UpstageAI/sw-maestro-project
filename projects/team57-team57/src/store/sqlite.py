"""SQLite helper — connection, migrations, insert/query."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("DB_PATH", "data/review_ops.db"))
MIGRATION_DIR = Path("migrations")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_for_hash(text: str) -> str:
    """공백 collapse + lowercase + strip — hash 입력 정규화."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _hash_text(text: str) -> str:
    """SHA1 hex of normalized text."""
    return hashlib.sha1(_normalize_for_hash(text).encode("utf-8")).hexdigest()


def _reviews_has_hash_column(conn: sqlite3.Connection) -> bool:
    cols = conn.execute("PRAGMA table_info(reviews)").fetchall()
    return any(c["name"] == "raw_text_hash" for c in cols)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def run_migrations() -> None:
    """모든 .sql 파일을 정렬 순으로 실행. IF NOT EXISTS 패턴이라 idempotent.

    002_review_text_hash.sql 의 ``ALTER TABLE ... ADD COLUMN`` 은 SQLite 가
    ``IF NOT EXISTS`` 를 지원하지 않으므로, 이미 컬럼이 있으면 해당 스크립트를
    건너뛰어 멱등성을 보장한다.
    """
    with connect() as conn:
        for sql_path in sorted(MIGRATION_DIR.glob("*.sql")):
            sql = sql_path.read_text(encoding="utf-8")
            # raw_text_hash 컬럼 추가 마이그레이션은 컬럼 존재 시 ALTER 건너뜀
            if "ADD COLUMN raw_text_hash" in sql and _reviews_has_hash_column(conn):
                # ALTER 부분만 빼고 인덱스 생성 부분만 재실행 (idempotent)
                idx_only = "\n".join(
                    line for line in sql.splitlines() if "ADD COLUMN" not in line
                )
                conn.executescript(idx_only)
                continue
            conn.executescript(sql)

        # 기존 NULL hash 행 backfill (컬럼이 존재할 때만)
        if _reviews_has_hash_column(conn):
            _backfill_hashes()


def _backfill_hashes() -> int:
    """기존 NULL raw_text_hash 행들에 hash 채움. idempotent."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT review_id, raw_text FROM reviews WHERE raw_text_hash IS NULL"
        ).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE reviews SET raw_text_hash=? WHERE review_id=?",
                (_hash_text(row["raw_text"]), row["review_id"]),
            )
        return len(rows)


def upsert_place(place_id: str, display_name: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO places (place_id, display_name) VALUES (?, ?) "
            "ON CONFLICT(place_id) DO UPDATE SET display_name=excluded.display_name",
            (place_id, display_name),
        )


def insert_raw_review(
    review_id: str, place_id: str, raw_text: str, created_at: str
) -> bool:
    """mock 리뷰 시드 시 호출. 분류 결과는 graph 실행 후 update_classification로 채움.

    Return True if a new row was inserted, False if duplicate (skipped).
    중복 판정 기준: (place_id, sha1(normalize(raw_text))) UNIQUE.
    """
    h = _hash_text(raw_text)
    with connect() as conn:
        # INSERT OR IGNORE: PK 충돌(review_id) 또는 (place_id, raw_text_hash)
        # 부분 UNIQUE 인덱스 충돌 시 행 삽입을 건너뛴다.
        cur = conn.execute(
            """INSERT OR IGNORE INTO reviews
                  (review_id, place_id, raw_text, raw_text_hash, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (review_id, place_id, raw_text, h, created_at),
        )
        return cur.rowcount > 0


def update_classification(
    review_id: str,
    masked_text: str,
    sentiment: str,
    confidence: float,
    categories: list[dict],  # [{"category": "맛", "confidence": 0.8}, ...]
    risk_flag: bool,
    risk_reason: str | None,
) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE reviews
               SET masked_text=?, sentiment=?, confidence=?,
                   risk_flag=?, risk_reason=?, processed_at=?
               WHERE review_id=?""",
            (
                masked_text,
                sentiment,
                confidence,
                1 if risk_flag else 0,
                risk_reason,
                _now_iso(),
                review_id,
            ),
        )
        conn.execute(
            "DELETE FROM review_categories WHERE review_id=?", (review_id,)
        )
        conn.executemany(
            "INSERT INTO review_categories (review_id, category, confidence) VALUES (?, ?, ?)",
            [(review_id, c["category"], c["confidence"]) for c in categories],
        )


def insert_reply(
    review_id: str, draft_text: str, drafter_used: str
) -> str:
    reply_id = f"reply_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """INSERT INTO replies (reply_id, review_id, draft_text, drafter_used)
               VALUES (?, ?, ?, ?)""",
            (reply_id, review_id, draft_text, drafter_used),
        )
    return reply_id


def _lookup_reply_context(reply_id: str) -> tuple[str | None, str | None]:
    """reply_id 로부터 (place_id, review_id) 조회. audit 이벤트에 함께 기록.

    조회 실패 시 (None, None) 반환 — audit row 는 nullable FK 이므로 안전.
    """
    with connect() as conn:
        row = conn.execute(
            """SELECT r.review_id AS review_id, rv.place_id AS place_id
               FROM replies r
               JOIN reviews rv ON r.review_id = rv.review_id
               WHERE r.reply_id = ?""",
            (reply_id,),
        ).fetchone()
    if not row:
        return None, None
    return row["place_id"], row["review_id"]


def mark_reply_copied(reply_id: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE replies SET copied_at=? WHERE reply_id=?",
            (_now_iso(), reply_id),
        )
    # UX-2: audit row — '복사' 이벤트.
    place_id, review_id = _lookup_reply_context(reply_id)
    if place_id:
        insert_feedback_event(
            place_id=place_id,
            review_id=review_id,
            reply_id=reply_id,
            event_type="copy",
        )


def mark_reply_edited(reply_id: str, final_text: str) -> None:
    # UX-2: 변경 *전* 값 stash → after 와 함께 audit row 적재.
    with connect() as conn:
        prev = conn.execute(
            "SELECT final_text, draft_text FROM replies WHERE reply_id=?",
            (reply_id,),
        ).fetchone()
        before_text = (prev["final_text"] or prev["draft_text"]) if prev else None
        conn.execute(
            "UPDATE replies SET final_text=?, edited_at=?, copied_at=? WHERE reply_id=?",
            (final_text, _now_iso(), _now_iso(), reply_id),
        )
    place_id, review_id = _lookup_reply_context(reply_id)
    if place_id:
        insert_feedback_event(
            place_id=place_id,
            review_id=review_id,
            reply_id=reply_id,
            event_type="edit",
            before_text=before_text,
            after_text=final_text,
        )


# ---------------------------------------------------------------------------
# UX-2: feedback_events audit trail
# ---------------------------------------------------------------------------


def insert_feedback_event(
    *,
    place_id: str,
    review_id: str | None,
    reply_id: str | None,
    event_type: str,
    before_text: str | None = None,
    after_text: str | None = None,
    diff_hint: str | None = None,
) -> str:
    """audit row 삽입. event_id 반환.

    event_type 은 CHECK 제약(copy/edit/manual_add/diff_hint_generated) 외 값이면
    sqlite3.IntegrityError 발생.
    """
    eid = f"fe_{uuid.uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """INSERT INTO feedback_events
                  (event_id, place_id, review_id, reply_id, event_type,
                   before_text, after_text, diff_hint)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (eid, place_id, review_id, reply_id, event_type,
             before_text, after_text, diff_hint),
        )
    return eid


def list_feedback_events(place_id: str, *, limit: int = 5) -> list[sqlite3.Row]:
    """최근순 audit 이벤트 목록. UI 사이드바 expander 가 표시."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT * FROM feedback_events
               WHERE place_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (place_id, limit),
        ).fetchall()
    return rows


def list_reviews(place_id: str, limit: int = 50) -> list[sqlite3.Row]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT r.*, GROUP_CONCAT(rc.category) AS categories
               FROM reviews r
               LEFT JOIN review_categories rc ON r.review_id = rc.review_id
               WHERE r.place_id = ? AND r.processed_at IS NOT NULL
               GROUP BY r.review_id
               ORDER BY r.created_at DESC
               LIMIT ?""",
            (place_id, limit),
        ).fetchall()
    return rows


def get_unprocessed_reviews(place_id: str, limit: int) -> list[sqlite3.Row]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT * FROM reviews
               WHERE place_id = ? AND processed_at IS NULL
               ORDER BY created_at ASC
               LIMIT ?""",
            (place_id, limit),
        ).fetchall()
    return rows


def get_reply_for_review(review_id: str) -> sqlite3.Row | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM replies WHERE review_id=? ORDER BY created_at DESC LIMIT 1",
            (review_id,),
        ).fetchone()
    return row


def get_review_stats(place_id: str) -> dict:
    """매장 전체 처리된 리뷰의 통계.

    Returns: {
        "total": int,
        "by_sentiment": {"positive": n, "negative": n, "neutral": n},
        "by_category": {"맛": n, ...},   # 멀티라벨 — 한 리뷰가 2 카테고리면 둘 다 +1
        "by_sentiment_category": [{"sentiment", "category", "count"}, ...],  # cross
    }
    """
    with connect() as conn:
        total_row = conn.execute(
            """SELECT COUNT(*) AS c FROM reviews
               WHERE place_id = ? AND processed_at IS NOT NULL""",
            (place_id,),
        ).fetchone()
        total = total_row["c"] if total_row else 0

        by_sent: dict[str, int] = {}
        for r in conn.execute(
            """SELECT sentiment, COUNT(*) AS c FROM reviews
               WHERE place_id = ? AND processed_at IS NOT NULL AND sentiment IS NOT NULL
               GROUP BY sentiment""",
            (place_id,),
        ):
            by_sent[r["sentiment"]] = r["c"]

        by_cat: dict[str, int] = {}
        for r in conn.execute(
            """SELECT rc.category, COUNT(DISTINCT rc.review_id) AS c
               FROM review_categories rc
               JOIN reviews r ON rc.review_id = r.review_id
               WHERE r.place_id = ? AND r.processed_at IS NOT NULL
               GROUP BY rc.category""",
            (place_id,),
        ):
            by_cat[r["category"]] = r["c"]

        cross: list[dict] = []
        for r in conn.execute(
            """SELECT r.sentiment, rc.category, COUNT(DISTINCT rc.review_id) AS c
               FROM review_categories rc
               JOIN reviews r ON rc.review_id = r.review_id
               WHERE r.place_id = ? AND r.processed_at IS NOT NULL
                 AND r.sentiment IS NOT NULL
               GROUP BY r.sentiment, rc.category""",
            (place_id,),
        ):
            cross.append(
                {"sentiment": r["sentiment"], "category": r["category"], "count": r["c"]}
            )

    return {
        "total": total,
        "by_sentiment": by_sent,
        "by_category": by_cat,
        "by_sentiment_category": cross,
    }


def query_top3_negative_categories(place_id: str, days: int = 28) -> list[dict]:
    """SQL tool 내부 구현 — 카테고리별 부정 빈도 TOP 3."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT rc.category, COUNT(*) AS freq
               FROM review_categories rc
               JOIN reviews r ON rc.review_id = r.review_id
               WHERE r.place_id = ?
                 AND r.sentiment = 'negative'
                 AND r.created_at >= datetime('now', ?)
               GROUP BY rc.category
               ORDER BY freq DESC
               LIMIT 3""",
            (place_id, f"-{days} days"),
        ).fetchall()
    return [{"category": r["category"], "freq": r["freq"]} for r in rows]


def reset_database() -> None:
    """발표 직전 깨끗한 상태 복원용. 모든 테이블 drop 후 migration 재실행."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    run_migrations()
