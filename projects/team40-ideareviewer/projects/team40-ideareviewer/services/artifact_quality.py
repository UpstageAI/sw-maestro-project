"""Deterministic quality checks for intermediate LLM artifacts."""

from __future__ import annotations

from typing import Literal

from schemas import (
    PointFeedback,
    QualityFlag,
    ReactionPoint,
    ServicePlanInput,
    TargetUserPersonaCard,
)
from services.brief_evidence import (
    has_brief_feature_overlap,
    introduces_unsupported_solution,
    numeric_terms,
)

QualityLevel = Literal["pass", "weak", "fail"]


def _persona_evidence_text(persona: TargetUserPersonaCard) -> str:
    return " ".join([
        persona.display_name,
        persona.age_group or "",
        persona.sex or "",
        persona.occupation or "",
        persona.region or "",
        persona.one_line_summary,
        persona.life_context,
        " ".join(persona.user_goals),
        " ".join(persona.pain_points),
        " ".join(persona.positive_triggers),
        " ".join(persona.negative_triggers),
    ])


def _has_unsupported_numeric_claim(
    text: str,
    brief: ServicePlanInput,
    persona: TargetUserPersonaCard,
) -> bool:
    claims = numeric_terms(text)
    if not claims:
        return False
    evidence = numeric_terms(" ".join([
        brief.raw_text or "",
        brief.title or "",
        brief.description or "",
        brief.target or "",
        " ".join(brief.key_features),
        brief.concerns or "",
        _persona_evidence_text(persona),
    ]))
    return bool(claims - evidence)


def assess_reaction_point(
    point: ReactionPoint,
    brief: ServicePlanInput,
    persona: TargetUserPersonaCard,
) -> tuple[QualityLevel, list[QualityFlag]]:
    text = f"{point.title} {point.detail}"
    flags: list[QualityFlag] = []
    if introduces_unsupported_solution(text, brief):
        flags.append(QualityFlag(
            code="unsupported_solution",
            severity="fail",
            message="서비스 기획안에 없는 해결책이나 기능을 언급했습니다.",
            point_id=point.point_id,
        ))
    if _has_unsupported_numeric_claim(text, brief, persona):
        flags.append(QualityFlag(
            code="unsupported_numeric_claim",
            severity="fail",
            message="기획서나 페르소나 근거에 없는 숫자/비율 주장을 포함했습니다.",
            point_id=point.point_id,
        ))
    if not has_brief_feature_overlap(text, brief):
        flags.append(QualityFlag(
            code="no_brief_feature_overlap",
            severity="fail",
            message="기획안의 핵심 기능과 직접 연결되지 않았습니다.",
            point_id=point.point_id,
        ))
    persona_terms = " ".join([
        persona.one_line_summary,
        persona.life_context,
        " ".join(persona.user_goals),
        " ".join(persona.pain_points),
    ])
    if not any(term in text for term in persona_terms.split() if len(term) >= 2):
        flags.append(QualityFlag(
            code="weak_persona_context",
            severity="weak",
            message="페르소나의 구체적 맥락 연결이 약합니다.",
            point_id=point.point_id,
        ))
    if any(flag.severity == "fail" for flag in flags):
        return "fail", flags
    if flags:
        return "weak", flags
    return "pass", []


def assess_feedback(
    feedback: PointFeedback,
    brief: ServicePlanInput,
) -> tuple[QualityLevel, list[QualityFlag]]:
    flags: list[QualityFlag] = []
    if introduces_unsupported_solution(feedback.comment, brief):
        flags.append(QualityFlag(
            code="unsupported_solution",
            severity="fail",
            message="교차 리뷰가 기획안에 없는 해결책이나 기능을 제안했습니다.",
            point_id=feedback.target_point_id,
        ))
    if len(feedback.comment.strip()) < 30:
        flags.append(QualityFlag(
            code="too_short",
            severity="weak",
            message="교차 리뷰 코멘트가 너무 짧아 판단 근거가 약합니다.",
            point_id=feedback.target_point_id,
        ))
    if any(flag.severity == "fail" for flag in flags):
        return "fail", flags
    if flags:
        return "weak", flags
    return "pass", []
