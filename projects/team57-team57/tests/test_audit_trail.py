"""UX-2: feedback_events audit trail 테스트.

검증 포인트:
- insert_feedback_event + list_feedback_events 동작
- mark_reply_edited 가 before/after 함께 audit row 생성
- mark_reply_copied 가 audit row 생성
- list_feedback_events 정렬(created_at DESC)
- CHECK 제약 — 알 수 없는 event_type 거부
"""

from __future__ import annotations

import importlib
import os
import sqlite3
import time
from pathlib import Path

import pytest

# 모든 테스트는 mock 모드 강제 (이 테스트 자체는 LLM 호출 없음 — 안전 기본값)
os.environ["REVIEW_OPS_LLM"] = "mock"
os.environ.pop("UPSTAGE_API_KEY", None)


@pytest.fixture()
def db_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """매 테스트마다 임시 DB 경로로 sqlite 모듈을 reload."""
    db_file = tmp_path / "test_audit.db"
    monkeypatch.setenv("DB_PATH", str(db_file))

    import src.store.sqlite as sqlite_mod

    sqlite_mod = importlib.reload(sqlite_mod)
    sqlite_mod.run_migrations()
    return sqlite_mod


def _seed_place_and_review(db_module, place_id: str = "PLACE_T", review_id: str = "REV_T") -> tuple[str, str, str]:
    """place + review + reply 시드. (place_id, review_id, reply_id) 반환."""
    db_module.upsert_place(place_id, "감사 테스트")
    db_module.insert_raw_review(
        review_id, place_id, "맛있어요", "2026-05-01T00:00:00Z"
    )
    reply_id = db_module.insert_reply(
        review_id=review_id, draft_text="감사합니다 초안", drafter_used="thanks"
    )
    return place_id, review_id, reply_id


# --- 기본 insert/list -------------------------------------------------------


def test_insert_and_list_feedback_event(db_module):
    place_id, review_id, reply_id = _seed_place_and_review(db_module)
    eid = db_module.insert_feedback_event(
        place_id=place_id,
        review_id=review_id,
        reply_id=reply_id,
        event_type="manual_add",
        before_text=None,
        after_text="사장님 작성 답글",
    )
    assert eid.startswith("fe_")

    events = db_module.list_feedback_events(place_id, limit=5)
    assert len(events) == 1
    assert events[0]["event_type"] == "manual_add"
    assert events[0]["after_text"] == "사장님 작성 답글"
    assert events[0]["before_text"] is None


# --- mark_reply_edited 가 audit row 자동 생성 ------------------------------


def test_mark_reply_edited_creates_audit_row(db_module):
    place_id, review_id, reply_id = _seed_place_and_review(db_module)

    db_module.mark_reply_edited(reply_id, "사장 최종본")
    events = db_module.list_feedback_events(place_id, limit=5)
    assert len(events) == 1
    ev = events[0]
    assert ev["event_type"] == "edit"
    assert ev["reply_id"] == reply_id
    assert ev["review_id"] == review_id
    assert ev["before_text"] == "감사합니다 초안"  # 직전 final_text 가 NULL 이라 draft_text 가 before
    assert ev["after_text"] == "사장 최종본"


def test_mark_reply_edited_twice_keeps_both(db_module):
    place_id, review_id, reply_id = _seed_place_and_review(db_module)

    db_module.mark_reply_edited(reply_id, "첫 수정")
    time.sleep(1.05)  # SQLite 의 datetime('now') 는 초 단위 → 1초+ 간격으로 정렬 보장
    db_module.mark_reply_edited(reply_id, "두 번째 수정")

    events = db_module.list_feedback_events(place_id, limit=10)
    assert len(events) == 2
    # 최신순 정렬 → 두 번째 수정이 0번
    assert events[0]["before_text"] == "첫 수정"
    assert events[0]["after_text"] == "두 번째 수정"
    assert events[1]["before_text"] == "감사합니다 초안"
    assert events[1]["after_text"] == "첫 수정"


# --- mark_reply_copied --------------------------------------------------------


def test_mark_reply_copied_creates_audit_row(db_module):
    place_id, review_id, reply_id = _seed_place_and_review(db_module)

    db_module.mark_reply_copied(reply_id)
    events = db_module.list_feedback_events(place_id, limit=5)
    assert len(events) == 1
    assert events[0]["event_type"] == "copy"
    assert events[0]["reply_id"] == reply_id
    assert events[0]["before_text"] is None
    assert events[0]["after_text"] is None


# --- 정렬 ------------------------------------------------------------------


def test_list_feedback_events_ordered_desc(db_module):
    place_id, _, reply_id = _seed_place_and_review(db_module)

    db_module.insert_feedback_event(
        place_id=place_id, review_id=None, reply_id=None,
        event_type="manual_add", after_text="첫번째",
    )
    time.sleep(1.05)
    db_module.insert_feedback_event(
        place_id=place_id, review_id=None, reply_id=None,
        event_type="manual_add", after_text="두번째",
    )
    time.sleep(1.05)
    db_module.insert_feedback_event(
        place_id=place_id, review_id=None, reply_id=None,
        event_type="manual_add", after_text="세번째",
    )

    events = db_module.list_feedback_events(place_id, limit=10)
    afters = [e["after_text"] for e in events]
    assert afters == ["세번째", "두번째", "첫번째"]


# --- limit 동작 ------------------------------------------------------------


def test_list_feedback_events_respects_limit(db_module):
    place_id, _, _ = _seed_place_and_review(db_module)
    for i in range(5):
        db_module.insert_feedback_event(
            place_id=place_id, review_id=None, reply_id=None,
            event_type="manual_add", after_text=f"sample_{i}",
        )
    assert len(db_module.list_feedback_events(place_id, limit=3)) == 3
    assert len(db_module.list_feedback_events(place_id, limit=10)) == 5


# --- CHECK 제약 -------------------------------------------------------------


def test_event_type_check_constraint_rejects_unknown(db_module):
    place_id, _, _ = _seed_place_and_review(db_module)
    with pytest.raises(sqlite3.IntegrityError):
        db_module.insert_feedback_event(
            place_id=place_id,
            review_id=None,
            reply_id=None,
            event_type="invalid_kind",
        )


# --- 다른 매장 이력은 섞이지 않음 ------------------------------------------


def test_list_feedback_events_scoped_to_place(db_module):
    place_a, _, _ = _seed_place_and_review(db_module, "PLACE_A", "REV_A")
    place_b, _, _ = _seed_place_and_review(db_module, "PLACE_B", "REV_B")

    db_module.insert_feedback_event(
        place_id=place_a, review_id=None, reply_id=None,
        event_type="manual_add", after_text="A의 답글",
    )
    db_module.insert_feedback_event(
        place_id=place_b, review_id=None, reply_id=None,
        event_type="manual_add", after_text="B의 답글",
    )

    a_events = db_module.list_feedback_events(place_a, limit=10)
    b_events = db_module.list_feedback_events(place_b, limit=10)
    assert [e["after_text"] for e in a_events] == ["A의 답글"]
    assert [e["after_text"] for e in b_events] == ["B의 답글"]
