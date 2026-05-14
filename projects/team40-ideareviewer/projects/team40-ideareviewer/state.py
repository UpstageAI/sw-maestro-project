"""전원 공유 — LangGraph ProjectState TypedDict. 임의 수정 금지."""

from typing import TypedDict

from schemas import (
    Opinion,
    OpinionQualityReport,
    PersonaSelectionReason,
    Review,
    ReviewQualityReport,
    ServicePlanInput,
    TargetUserPersonaCard,
)


class ProjectState(TypedDict, total=False):
    raw_input: str
    brief: ServicePlanInput
    persona_a: TargetUserPersonaCard
    persona_b: TargetUserPersonaCard
    persona_selection_reason: PersonaSelectionReason
    opinion_a: Opinion
    opinion_b: Opinion
    opinion_quality_a: OpinionQualityReport
    opinion_quality_b: OpinionQualityReport
    review_a: Review
    review_b: Review
    review_quality_a: ReviewQualityReport
    review_quality_b: ReviewQualityReport
    final_review_text: str


__all__ = ["ProjectState"]
