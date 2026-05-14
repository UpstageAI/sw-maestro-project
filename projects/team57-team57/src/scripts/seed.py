"""Seed script — JSON → SQLite + Memory Store dump.

Usage: `make seed` 또는 `uv run python -m src.scripts.seed`.

UI(Wave 3)의 원클릭 리셋 버튼은 ``seed_all(reset=True)`` 를 직접 호출한다.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from src.store import sqlite as db
from src.store.memory import save_dump, seed_from_json

DATA_DIR = Path("data")
SEED_PLACES = DATA_DIR / "seed_places.json"


def _seed_places_and_memory() -> tuple[list[dict], int, int]:
    """Memory Store에 매장 메타·톤샘플·피드백을 시드. SQLite places 테이블도 채움.

    Returns (places, tone_samples_count, feedback_hints_count).
    """
    if not SEED_PLACES.exists():
        sys.exit(f"FATAL: {SEED_PLACES} 가 없습니다.")

    payload = json.loads(SEED_PLACES.read_text(encoding="utf-8"))
    places = payload["places"]

    seed_from_json(places)
    save_dump()

    tone_samples = 0
    feedback_hints = 0
    for p in places:
        db.upsert_place(p["place_id"], p["display_name"])
        tone_samples += len(p.get("tone_samples", []))
        feedback_hints += len(p.get("feedback", []))

    return places, tone_samples, feedback_hints


def _seed_reviews(place_id: str) -> tuple[int, int]:
    """data/mock_reviews_<place_id>.json 을 SQLite reviews 테이블에 insert.

    Returns (inserted, skipped_duplicate). 본문 해시 기준 중복은 자동 스킵.
    """
    path = DATA_DIR / f"mock_reviews_{place_id}.json"
    if not path.exists():
        print(f"  (skip) mock reviews 없음: {path}")
        return 0, 0
    items = json.loads(path.read_text(encoding="utf-8"))
    inserted = 0
    skipped = 0
    for it in items:
        ok = db.insert_raw_review(
            review_id=it["review_id"],
            place_id=place_id,
            raw_text=it["review_text"],
            created_at=it["created_at"],
        )
        if ok:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def seed_all(reset: bool = True) -> dict:
    """전체 시드 워크플로우 (UI의 '데모 리셋' 버튼이 호출).

    Args:
        reset: True면 DB 파일을 삭제 후 마이그레이션 재실행. False면 기존 DB에
            마이그레이션만 보장.

    Returns:
        {
          "places": int,
          "reviews_inserted": int,
          "reviews_skipped_duplicate": int,
          "tone_samples": int,
          "feedback_hints": int,
        }
    """
    if reset:
        db.reset_database()
    else:
        db.run_migrations()

    places, tone_samples, feedback_hints = _seed_places_and_memory()

    total_inserted = 0
    total_skipped = 0
    for p in places:
        ins, skp = _seed_reviews(p["place_id"])
        total_inserted += ins
        total_skipped += skp

    return {
        "places": len(places),
        "reviews_inserted": total_inserted,
        "reviews_skipped_duplicate": total_skipped,
        "tone_samples": tone_samples,
        "feedback_hints": feedback_hints,
    }


def main() -> None:
    print("[1/3] DB 마이그레이션 + 리셋...")
    summary = seed_all(reset=True)

    print("[2/3] 시드 매장:")
    print(f"   - 매장 {summary['places']}개")
    print(f"   - 톤샘플 {summary['tone_samples']}건")
    print(f"   - 피드백 힌트 {summary['feedback_hints']}건")

    print("[3/3] mock 리뷰 SQLite insert:")
    print(f"   - 신규 적재 {summary['reviews_inserted']}건")
    print(f"   - 중복 스킵 {summary['reviews_skipped_duplicate']}건")

    print()
    print(f"DB:    {os.getenv('DB_PATH', 'data/review_ops.db')}")
    print(f"Store: {os.getenv('STORE_DUMP_PATH', 'data/store_dump.json')}")
    print(f"Summary: {summary}")
    print("\n다음: make run")


if __name__ == "__main__":
    main()
