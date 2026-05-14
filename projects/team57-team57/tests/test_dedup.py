"""P0-4: 본문 해시 기반 리뷰 중복 감지 테스트.

`(place_id, sha1(normalize(raw_text)))` UNIQUE 인덱스가 두 번째 insert를 스킵해야 한다.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture()
def db_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """매 테스트마다 임시 DB 경로로 sqlite 모듈을 reload."""
    db_file = tmp_path / "test_review_ops.db"
    monkeypatch.setenv("DB_PATH", str(db_file))

    # 모듈 캐시에 module-level DB_PATH 가 박혀있으므로 reload 로 새 env 반영
    import src.store.sqlite as sqlite_mod

    sqlite_mod = importlib.reload(sqlite_mod)
    sqlite_mod.run_migrations()
    return sqlite_mod


# --- 정규화 / 해시 단위 테스트 ----------------------------------------------


def test_normalize_collapses_whitespace(db_module):
    assert db_module._normalize_for_hash("  Foo  Bar  ") == "foo bar"


def test_normalize_handles_none_and_empty(db_module):
    assert db_module._normalize_for_hash("") == ""
    assert db_module._normalize_for_hash(None) == ""  # type: ignore[arg-type]


def test_hash_deterministic(db_module):
    h1 = db_module._hash_text("같은 본문입니다.")
    h2 = db_module._hash_text("같은 본문입니다.")
    assert h1 == h2


def test_hash_normalization_equivalence(db_module):
    assert db_module._hash_text("  Foo  Bar  ") == db_module._hash_text("foo bar")


# --- insert_raw_review 중복 동작 -------------------------------------------


def _place(db_module, pid: str = "PLACE_TEST") -> str:
    db_module.upsert_place(pid, "테스트 매장")
    return pid


def test_insert_same_review_twice_keeps_one(db_module):
    pid = _place(db_module)
    ok1 = db_module.insert_raw_review("REV_A", pid, "맛있어요!", "2026-05-01T00:00:00Z")
    ok2 = db_module.insert_raw_review("REV_B", pid, "맛있어요!", "2026-05-02T00:00:00Z")
    assert ok1 is True
    assert ok2 is False

    # processed_at NULL 이라 list_reviews 가 비어있으므로 직접 카운트
    with db_module.connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS c FROM reviews WHERE place_id=?", (pid,)
        ).fetchone()["c"]
    assert n == 1


def test_different_text_inserts_both(db_module):
    pid = _place(db_module)
    assert db_module.insert_raw_review("REV_1", pid, "맛있어요", "2026-05-01T00:00:00Z") is True
    assert db_module.insert_raw_review("REV_2", pid, "별로예요", "2026-05-01T00:00:00Z") is True

    with db_module.connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS c FROM reviews WHERE place_id=?", (pid,)
        ).fetchone()["c"]
    assert n == 2


def test_different_place_same_text_inserts_both(db_module):
    pid_a = _place(db_module, "PLACE_A")
    pid_b = _place(db_module, "PLACE_B")
    assert db_module.insert_raw_review("REV_X1", pid_a, "동일 본문", "2026-05-01T00:00:00Z") is True
    assert db_module.insert_raw_review("REV_X2", pid_b, "동일 본문", "2026-05-01T00:00:00Z") is True

    with db_module.connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM reviews").fetchone()["c"]
    assert n == 2


def test_whitespace_only_difference_still_dedup(db_module):
    pid = _place(db_module)
    assert (
        db_module.insert_raw_review("REV_W1", pid, "맛있  어요", "2026-05-01T00:00:00Z")
        is True
    )
    # 공백 다수 vs 단일 — normalize 후 동일
    assert (
        db_module.insert_raw_review("REV_W2", pid, "맛있 어요", "2026-05-02T00:00:00Z")
        is False
    )


# --- backfill --------------------------------------------------------------


def test_backfill_hashes(db_module):
    pid = _place(db_module)
    # 컬럼은 있지만 NULL 인 행을 강제로 삽입 (정상 경로는 항상 hash 가 채워짐)
    with db_module.connect() as conn:
        conn.execute(
            """INSERT INTO reviews (review_id, place_id, raw_text, raw_text_hash, created_at)
               VALUES (?, ?, ?, NULL, ?)""",
            ("REV_NULL", pid, "백필 대상 본문", "2026-05-01T00:00:00Z"),
        )

    filled = db_module._backfill_hashes()
    assert filled == 1

    with db_module.connect() as conn:
        row = conn.execute(
            "SELECT raw_text_hash FROM reviews WHERE review_id=?", ("REV_NULL",)
        ).fetchone()
    assert row["raw_text_hash"] == db_module._hash_text("백필 대상 본문")

    # idempotent — 두 번째 호출은 0건
    assert db_module._backfill_hashes() == 0
