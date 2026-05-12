"""f4_supervisor — 두 페르소나 의견과 교차 리뷰를 최종 리뷰 텍스트로 종합."""

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage

from schemas import Opinion, Review, ServicePlanInput, TargetUserPersonaCard
from state import ProjectState

load_dotenv()

_llm = ChatUpstage(model="solar-pro3")

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 서비스 기획 리뷰를 정리하는 중립적인 슈퍼바이저입니다. "
        "페르소나처럼 말하지 말고, 제품 기획자가 바로 읽을 수 있는 최종 리뷰를 작성하세요. "
        "입력에 없는 기능, 사용 맥락, 시장 사실은 만들어내지 마세요. "
        "반드시 아래 다섯 섹션을 같은 순서로 작성하세요:\n"
        "1. 종합 판단\n"
        "2. 긍정 신호\n"
        "3. 주요 우려\n"
        "4. 페르소나 간 차이\n"
        "5. 다음 검증 포인트",
    ),
    (
        "human",
        "## 서비스 기획안\n{brief}\n\n"
        "## 페르소나 A\n{persona_a}\n\n"
        "## 페르소나 B\n{persona_b}\n\n"
        "## 페르소나 A의 1차 의견\n{opinion_a}\n\n"
        "## 페르소나 B의 1차 의견\n{opinion_b}\n\n"
        "## 페르소나 A가 B 의견을 읽고 남긴 리뷰\n{review_a}\n\n"
        "## 페르소나 B가 A 의견을 읽고 남긴 리뷰\n{review_b}\n\n"
        "위 내용을 종합해 최종 리뷰를 작성하세요.",
    ),
])


def _format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 없음"


def _format_brief(brief: ServicePlanInput) -> str:
    features = _format_list(brief.key_features)
    return (
        f"제목: {brief.title or '-'}\n"
        f"설명: {brief.description or '-'}\n"
        f"타겟: {brief.target or '-'}\n"
        f"핵심 기능:\n{features}\n"
        f"우려사항: {brief.concerns or '-'}"
    )


def _format_persona(persona: TargetUserPersonaCard) -> str:
    return (
        f"ID: {persona.card_id}\n"
        f"이름: {persona.display_name}\n"
        f"연령대/성별/직업/지역: "
        f"{persona.age_group or '-'} / {persona.sex or '-'} / "
        f"{persona.occupation or '-'} / {persona.region or '-'}\n"
        f"요약: {persona.one_line_summary}\n"
        f"생활 맥락: {persona.life_context}\n"
        f"목표:\n{_format_list(persona.user_goals)}\n"
        f"불편함:\n{_format_list(persona.pain_points)}\n"
        f"긍정 트리거:\n{_format_list(persona.positive_triggers)}\n"
        f"부정 트리거:\n{_format_list(persona.negative_triggers)}\n"
        f"말투: {persona.speaking_style}"
    )


def _format_opinion(opinion: Opinion) -> str:
    positive = "\n".join(
        f"- [{point.point_id}] {point.title}: {point.detail}"
        for point in opinion.positive_points
    )
    negative = "\n".join(
        f"- [{point.point_id}] {point.title}: {point.detail}"
        for point in opinion.negative_points
    )
    would_use = "사용할 것" if opinion.would_use else "사용 안 할 것"
    return (
        f"persona_id: {opinion.persona_id}\n"
        f"긍정 포인트:\n{positive or '- 없음'}\n"
        f"부정 포인트:\n{negative or '- 없음'}\n"
        f"사용 의향: {would_use}\n"
        f"사용 의향 이유: {opinion.would_use_description or '-'}"
    )


def _format_review(review: Review) -> str:
    feedbacks = "\n".join(
        f"- [{feedback.target_point_id}] {feedback.agreement}: {feedback.comment}"
        for feedback in review.point_feedbacks
    )
    revised = "사용할 것" if review.revised_would_use else "사용 안 할 것"
    return (
        f"reviewer_id: {review.reviewer_id}\n"
        f"target_id: {review.target_id}\n"
        f"포인트별 피드백:\n{feedbacks or '- 없음'}\n"
        f"종합 소감: {review.overall_comment}\n"
        f"수정된 사용 의향: {revised}"
    )


def _build_supervisor_prompt_vars(state: ProjectState) -> dict[str, str]:
    return {
        "brief": _format_brief(state["brief"]),
        "persona_a": _format_persona(state["persona_a"]),
        "persona_b": _format_persona(state["persona_b"]),
        "opinion_a": _format_opinion(state["opinion_a"]),
        "opinion_b": _format_opinion(state["opinion_b"]),
        "review_a": _format_review(state["review_a"]),
        "review_b": _format_review(state["review_b"]),
    }


def supervisor_finalize(state: ProjectState) -> dict:
    """교차 리뷰까지 완료된 state를 읽어 최종 사용자용 리뷰 텍스트를 생성."""
    chain = _PROMPT | _llm | StrOutputParser()
    final_review_text = chain.invoke(_build_supervisor_prompt_vars(state))
    return {"final_review_text": final_review_text.strip()}
