from __future__ import annotations

from src.llm.mock_provider import MockProvider


def test_mock_provider_classifies_and_drafts() -> None:
    provider = MockProvider()
    analysis = provider.classify_review(
        review_text="아메리카노는 맛있는데 줄이 너무 길어요.",
        menu_items=["아메리카노", "카페라떼"],
    )

    assert analysis.sentiment == "중립"
    assert "맛" in analysis.categories
    assert "대기시간" in analysis.categories
    assert analysis.menu_tags == ["아메리카노"]

    draft = provider.draft_reply(
        review_text="아메리카노는 맛있는데 줄이 너무 길어요.",
        sentiment=analysis.sentiment,
        categories=analysis.categories,
        store_name="테스트 카페",
        tone="정중체",
        menu_items=["아메리카노", "카페라떼"],
        reply_samples=["리뷰 감사합니다."],
        recent_feedback_samples=[],
    )

    assert len(draft.replies) == 2
    assert all(reply.endswith("겠습니다.") or "감사" in reply for reply in draft.replies)

