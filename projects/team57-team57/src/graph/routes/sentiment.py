"""Conditional edge function — sentiment + confidence 기반 router.

P0-2/P0-3 도입 후: lang_skip 또는 classification_failed 가 우선순위 최상위 → noop_drafter.
나머지는 기존 4분기 (thanks/apology/apology_lowconf/neutral).
"""

from __future__ import annotations

CONFIDENCE_THRESHOLD = 0.7


def route_by_sentiment(state: dict) -> str:
    # P0-2/P0-3: 비한국어 또는 분류 실패 → drafter LLM 호출 건너뛰기
    if state.get("lang_skip") or state.get("classification_failed"):
        return "noop_drafter"

    sentiment = state.get("sentiment")
    if sentiment == "positive":
        return "thanks_drafter"
    if sentiment == "neutral":
        return "neutral_drafter"
    # negative
    if state.get("confidence", 0.0) >= CONFIDENCE_THRESHOLD:
        return "apology_drafter"
    return "apology_drafter_lowconf"
