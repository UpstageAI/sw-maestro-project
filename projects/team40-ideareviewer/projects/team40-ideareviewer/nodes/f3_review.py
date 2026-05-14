"""f3_review — 상대 페르소나 의견 교차 리뷰 생성."""

from typing import Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from pydantic import BaseModel, Field

from schemas import (
    Opinion,
    OpinionQualityReport,
    PointFeedback,
    QualityFlag,
    ReactionPoint,
    Review,
    ReviewQualityReport,
    ServicePlanInput,
    TargetUserPersonaCard,
)
from services.artifact_quality import assess_feedback

load_dotenv()


class _PointReviewDraft(BaseModel):
    agreement: Literal["agree", "disagree"]
    comment: str = Field(
        description="상대 포인트 하나에 대한 반응. 새 기능을 제안하지 말고 내 사용 판단 변화만 2~3문장으로 설명."
    )
    effect_on_would_use: Literal["increase", "decrease", "same"] = "same"


_point_llm = ChatUpstage(model="solar-pro3").with_structured_output(_PointReviewDraft)

_POINT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 아래 페르소나입니다. 상대 의견의 포인트 하나만 읽고 반응하세요. "
        "서비스 기획안에 없는 새 기능, 인증, 자동화, 모니터링, 알고리즘을 제안하지 마세요. "
        "상대 의견을 반복하지 말고 내 사용 판단이 어떻게 달라지는지만 말하세요.\n\n"
        "## 내 페르소나\n"
        "이름: {display_name}\n"
        "요약: {one_line_summary}\n"
        "생활 맥락: {life_context}\n"
        "목표: {user_goals}\n"
        "불편함: {pain_points}\n"
        "말투: {speaking_style}\n\n"
        "## 준수사항\n{guardrails}",
    ),
    (
        "human",
        "## 서비스 기획안\n"
        "제목: {title}\n"
        "설명: {description}\n"
        "핵심 기능:\n{key_features}\n"
        "우려사항: {concerns}\n\n"
        "## 상대 포인트\n"
        "point_id: {point_id}\n"
        "title: {point_title}\n"
        "detail: {point_detail}\n\n"
        "이 포인트에 대해 동의/반대와 이유를 작성하세요.",
    ),
])


def _reviewable_points(
    target: Opinion,
    quality: OpinionQualityReport | None,
) -> list[ReactionPoint]:
    points = [*target.positive_points, *target.negative_points]
    if quality is None:
        return points
    blocked = set(quality.fail_point_ids)
    return [point for point in points if point.point_id not in blocked]


def _generate_point_feedback(
    reviewer: TargetUserPersonaCard,
    brief: ServicePlanInput,
    point: ReactionPoint,
) -> PointFeedback:
    chain = _POINT_PROMPT | _point_llm
    draft: _PointReviewDraft = chain.invoke({
        "display_name": reviewer.display_name,
        "one_line_summary": reviewer.one_line_summary,
        "life_context": reviewer.life_context,
        "user_goals": "\n".join(f"- {g}" for g in reviewer.user_goals),
        "pain_points": "\n".join(f"- {p}" for p in reviewer.pain_points),
        "speaking_style": reviewer.speaking_style,
        "guardrails": "\n".join(f"- {g}" for g in reviewer.guardrails),
        "title": brief.title or "",
        "description": brief.description or "",
        "key_features": "\n".join(f"- {f}" for f in brief.key_features),
        "concerns": brief.concerns or "",
        "point_id": point.point_id,
        "point_title": point.title,
        "point_detail": point.detail,
    })
    return PointFeedback(
        target_point_id=point.point_id,
        agreement=draft.agreement,
        comment=draft.comment,
    )


def _build_review_quality_report(
    *,
    reviewer_id: str,
    target: Opinion,
    target_quality: OpinionQualityReport | None,
    feedbacks: list[PointFeedback],
    brief: ServicePlanInput,
) -> ReviewQualityReport:
    report = ReviewQualityReport(reviewer_id=reviewer_id, target_id=target.persona_id)
    for feedback in feedbacks:
        level, flags = assess_feedback(feedback, brief)
        report.flags.extend(flags)
        if level == "pass":
            report.pass_feedback_ids.append(feedback.target_point_id)
        elif level == "weak":
            report.weak_feedback_ids.append(feedback.target_point_id)
        else:
            report.fail_feedback_ids.append(feedback.target_point_id)
    if target_quality:
        for point_id in target_quality.fail_point_ids:
            report.flags.append(QualityFlag(
                code="skipped_failed_opinion_point",
                severity="weak",
                message="품질 기준을 통과하지 못한 1차 의견 포인트라 교차 리뷰에서 제외했습니다.",
                point_id=point_id,
            ))
    return report


def _review_overall_comment(feedbacks: list[PointFeedback]) -> str:
    if not feedbacks:
        return "리뷰 가능한 포인트가 부족해 종합 판단을 보류합니다."
    disagree_count = sum(1 for item in feedbacks if item.agreement == "disagree")
    if disagree_count > len(feedbacks) / 2:
        return "상대 의견을 검토한 결과 사용 판단을 낮추는 우려가 더 많았습니다."
    return "상대 의견을 검토한 결과 일부 우려는 있지만 사용 판단을 크게 낮추지는 않았습니다."


def _revised_would_use(feedbacks: list[PointFeedback]) -> bool:
    if not feedbacks:
        return False
    disagree_count = sum(1 for item in feedbacks if item.agreement == "disagree")
    return disagree_count <= len(feedbacks) / 2


def generate_review(state: dict) -> dict:
    """Send로 파견된 노드. sub-state 구조: {reviewer, target_opinion, brief, slot}."""
    reviewer: TargetUserPersonaCard = state["reviewer"]
    target: Opinion = state["target_opinion"]
    target_quality: OpinionQualityReport | None = state.get("target_opinion_quality")
    brief: ServicePlanInput = state["brief"]
    slot: str = state["slot"]

    reviewable = _reviewable_points(target, target_quality)
    feedbacks = [
        _generate_point_feedback(reviewer, brief, point)
        for point in reviewable
    ]
    quality = _build_review_quality_report(
        reviewer_id=reviewer.card_id,
        target=target,
        target_quality=target_quality,
        feedbacks=feedbacks,
        brief=brief,
    )
    review = Review(
        reviewer_id=reviewer.card_id,
        target_id=target.persona_id,
        point_feedbacks=feedbacks,
        overall_comment=_review_overall_comment(feedbacks),
        revised_would_use=_revised_would_use(feedbacks),
    )
    return {
        f"review_{slot}": review,
        f"review_quality_{slot}": quality,
    }
