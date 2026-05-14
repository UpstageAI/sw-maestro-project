from __future__ import annotations

from pathlib import Path

from src.db.repository import ReviewAgentRepository


def test_repository_store_session_review_feedback_cycle(tmp_path: Path) -> None:
    repo = ReviewAgentRepository(tmp_path / "test.db")
    repo.initialize()

    store_id = repo.upsert_store(
        store_id=None,
        name="테스트 카페",
        business_type="카페",
        menu_items=["아메리카노", "카페라떼"],
        price_range="5000~10000원",
        reply_tone="정중체",
        reply_samples=["리뷰 감사합니다."],
    )
    assert store_id > 0

    session_id = repo.create_review_session(store_id=store_id, raw_input_text="리뷰 원문")
    review_id = repo.create_review(
        session_id=session_id,
        store_id=store_id,
        original_text="아메리카노 맛있어요",
        masked_text="아메리카노 맛있어요",
        sentiment="긍정",
        sentiment_confidence=0.91,
        categories=["맛"],
        menu_tags=["아메리카노"],
        generated_replies=["감사합니다."],
        status="analyzed",
    )

    repo.update_review_feedback(
        review_id=review_id,
        edited_reply="정성껏 준비하겠습니다.",
        selected_reply="감사합니다.",
        status="feedback_applied",
    )
    event_id = repo.create_feedback_event(
        store_id=store_id,
        review_id=review_id,
        feedback_type="edited_reply",
        before_value="감사합니다.",
        after_value="정성껏 준비하겠습니다.",
    )

    store = repo.get_store(store_id)
    review = repo.get_review(review_id)
    events = repo.list_feedback_events(store_id)
    recent = repo.list_recent_edited_replies(store_id)

    assert store is not None
    assert store.menu_items == ["아메리카노", "카페라떼"]
    assert review is not None
    assert review.edited_reply == "정성껏 준비하겠습니다."
    assert event_id == events[0].id
    assert recent == ["정성껏 준비하겠습니다."]

