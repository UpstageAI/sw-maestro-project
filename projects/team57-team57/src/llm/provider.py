from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ReviewClassification:
    sentiment: str
    confidence: float
    categories: list[str]
    menu_tags: list[str]
    rationale: str


@dataclass(slots=True)
class ReplyDraft:
    replies: list[str]
    safety_notes: list[str]


class LLMProvider(Protocol):
    provider_name: str

    def classify_review(self, *, review_text: str, menu_items: list[str]) -> ReviewClassification:
        ...

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
        ...


def get_provider() -> LLMProvider:
    configured = os.getenv("REVIEW_AGENT_LLM_PROVIDER", "auto").lower().strip()

    if configured == "mock":
        from src.llm.mock_provider import MockProvider

        return MockProvider()

    if configured == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        from src.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    if configured == "openai" and os.getenv("OPENAI_API_KEY"):
        from src.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()

    if os.getenv("ANTHROPIC_API_KEY"):
        from src.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    if os.getenv("OPENAI_API_KEY"):
        from src.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()

    from src.llm.mock_provider import MockProvider

    return MockProvider()
