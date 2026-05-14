"""전원 공유 — LangGraph ProjectState TypedDict. 임의 수정 금지."""

from typing import TypedDict

from schemas import (
    Opinion,
    Review,
    ServicePlanInput,
    TargetUserPersonaCard,
)


class ProjectState(TypedDict, total=False):
    raw_input: str
    brief: ServicePlanInput
    persona_a: TargetUserPersonaCard
    persona_b: TargetUserPersonaCard
    opinion_a: Opinion
    opinion_b: Opinion
    review_a: Review
    review_b: Review
    final_review_text: str


__all__ = ["ProjectState"]
