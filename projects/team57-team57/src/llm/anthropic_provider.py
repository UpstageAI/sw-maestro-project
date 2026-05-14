from __future__ import annotations

from src.llm.provider import ReplyDraft, ReviewClassification


class AnthropicProvider:
    provider_name = "anthropic"

    def classify_review(self, *, review_text: str, menu_items: list[str]) -> ReviewClassification:
        raise NotImplementedError("Anthropic provider will be implemented in a later stage.")

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
        raise NotImplementedError("Anthropic provider will be implemented in a later stage.")

