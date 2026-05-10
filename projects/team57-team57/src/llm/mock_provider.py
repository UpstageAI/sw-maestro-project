from __future__ import annotations

from src.llm.provider import ReplyDraft, ReviewClassification

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "맛": ("맛", "고소", "진하", "싱겁", "짜", "달", "디저트"),
    "서비스": ("친절", "응대", "불친절", "차갑", "주문 누락", "대응"),
    "가격": ("가격", "비싸", "가성비", "부담"),
    "대기시간": ("대기", "기다", "줄", "피크타임"),
    "위생": ("위생", "청소", "정리", "더럽", "테이블"),
}

POSITIVE_KEYWORDS = ("좋", "맛있", "친절", "만족", "고소", "추천", "또 올", "좋았")
NEGATIVE_KEYWORDS = ("아쉽", "별로", "늦", "길", "차갑", "불친절", "걱정", "누락", "비싸")


class MockProvider:
    provider_name = "mock"

    def classify_review(self, *, review_text: str, menu_items: list[str]) -> ReviewClassification:
        categories = [
            category
            for category, keywords in CATEGORY_KEYWORDS.items()
            if any(keyword in review_text for keyword in keywords)
        ]
        menu_tags = [item for item in menu_items if item and item in review_text]

        positive_hits = sum(keyword in review_text for keyword in POSITIVE_KEYWORDS)
        negative_hits = sum(keyword in review_text for keyword in NEGATIVE_KEYWORDS)

        if positive_hits and negative_hits:
            sentiment = "중립"
            confidence = 0.66
        elif negative_hits > positive_hits:
            sentiment = "부정"
            confidence = 0.82
        elif positive_hits > 0:
            sentiment = "긍정"
            confidence = 0.88
        else:
            sentiment = "중립"
            confidence = 0.60

        if not categories:
            categories = ["서비스"] if "직원" in review_text else ["맛"]

        rationale = "keyword-rule-based mock analysis"
        return ReviewClassification(
            sentiment=sentiment,
            confidence=confidence,
            categories=categories,
            menu_tags=menu_tags,
            rationale=rationale,
        )

    def draft_reply(
        self,
        *,
        review_text: str,
        sentiment: str,
        categories: list[str],
        store_name: str,
        tone: str,
        menu_items: list[str],
        reply_samples: list[str],
        recent_feedback_samples: list[str],
    ) -> ReplyDraft:
        menu_hint = f" {menu_items[0]} 관련 의견도 참고하겠습니다." if menu_items else ""
        sample_hint = reply_samples[0] if reply_samples else f"{store_name}를 찾아주셔서 감사합니다."
        feedback_hint = recent_feedback_samples[0] if recent_feedback_samples else ""

        if sentiment == "부정":
            replies = [
                f"불편을 드려 정말 죄송합니다. 말씀해주신 {'/'.join(categories)} 부분을 확인했고 더 나은 이용 경험을 드릴 수 있도록 점검하겠습니다.{menu_hint}",
                f"소중한 의견 남겨주셔서 감사합니다. 아쉬우셨던 {'/'.join(categories)} 부분을 매장에서 다시 살피고 개선하겠습니다."
            ]
        elif sentiment == "긍정":
            replies = [
                f"{sample_hint} 만족스러운 경험이 되었다니 정말 기쁩니다. 다음 방문 때도 좋은 맛과 서비스로 보답하겠습니다.",
                f"좋은 리뷰 감사합니다. 남겨주신 말씀 덕분에 큰 힘이 됩니다. 앞으로도 정성껏 준비하겠습니다."
            ]
        else:
            replies = [
                f"방문 후 의견 남겨주셔서 감사합니다. 말씀해주신 {'/'.join(categories)} 관련 내용을 참고해 더 안정적인 매장 경험을 드리겠습니다.",
                f"소중한 리뷰 감사합니다. 좋았던 점과 아쉬운 점을 함께 참고해 운영에 반영하겠습니다."
            ]

        if feedback_hint:
            replies[0] = f"{replies[0]} ({feedback_hint})"

        return ReplyDraft(replies=replies, safety_notes=["mock provider: monetary compensation promises excluded"])

