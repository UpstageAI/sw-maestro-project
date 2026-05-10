"""f3_review — 상대 페르소나 의견 교차 리뷰 생성."""

from typing import Literal

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from pydantic import BaseModel, Field

from schemas import Opinion, PointFeedback, Review, ServicePlanInput, TargetUserPersonaCard

load_dotenv()


# f2의 _ReactionPointDraft와 구조는 비슷하지만 목적이 다르다.
# 이 모델은 "상대 포인트에 동의/반대하는 피드백"을 LLM에서 받는 용도.
# target_point_id: f2에서 생성한 point_id(예: "70plus_pos_01")를 그대로 참조해야
# 나중에 어떤 포인트에 대한 피드백인지 추적할 수 있다.
class _PointFeedbackDraft(BaseModel):
    target_point_id: str = Field(description="리뷰 대상 포인트의 point_id (원문 그대로)")
    agreement: Literal["agree", "disagree"]
    comment: str = Field(
        description="이 포인트에 대한 의견. 내 삶의 경험과 연결해 구체적으로 3문장 이상 서술."
    )


# schemas.py의 Review에는 reviewer_id·target_id가 있지만 LLM이 결정할 필요가 없으므로
# 텍스트 필드만 받는 중간 모델을 별도로 정의한다.
class _ReviewDraft(BaseModel):
    point_feedbacks: list[_PointFeedbackDraft] = Field(
        description="상대 의견의 긍정·부정 포인트 전체에 대해 각각 동의/반대 여부와 이유를 서술."
    )
    overall_comment: str = Field(
        description="상대 의견 전체에 대한 종합 소감. 내 삶과 연결해 5문장 이상으로 서술."
    )
    revised_would_use: bool = Field(
        description="상대 의견을 읽은 뒤 내 사용 의향이 바뀌었는지 (최종 결론)"
    )


_llm = ChatUpstage(model="solar-pro3").with_structured_output(_ReviewDraft)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 아래 페르소나입니다. 반드시 이 페르소나의 시각과 말투로만 반응하세요.\n\n"
        "## 내 페르소나\n"
        "이름: {display_name}\n"
        "한 줄 요약: {one_line_summary}\n"
        "삶의 맥락: {life_context}\n"
        "목표: {user_goals}\n"
        "불편함: {pain_points}\n"
        "긍정 트리거: {positive_triggers}\n"
        "부정 트리거: {negative_triggers}\n"
        "말투: {speaking_style}\n\n"
        "## 작성 지침\n"
        "- 각 point_feedback의 comment는 내 삶의 구체적 상황과 연결해 3문장 이상 쓰세요.\n"
        "- overall_comment는 상대 의견이 내 생각을 바꿨는지, 어떤 부분이 공감됐는지 5문장 이상 쓰세요.\n"
        "- target_point_id는 원문 그대로 사용하세요 (수정 금지).\n"
        "- 말투는 speaking_style을 반드시 반영하세요.\n\n"
        "## 준수사항\n{guardrails}",
    ),
    (
        "human",
        "## 서비스 기획안\n"
        "제목: {title}\n"
        "설명: {description}\n\n"
        "## 상대방이 작성한 의견 (persona_id: {target_persona_id})\n"
        "긍정 포인트:\n{positive_points}\n"
        "부정 포인트:\n{negative_points}\n"
        "사용 의향: {would_use} — {would_use_description}\n\n"
        "위 의견을 읽고 각 포인트에 동의/반대 이유와 종합 소감을 작성해 주세요.",
    ),
])


def _format_points(points) -> str:
    # LLM 프롬프트에 넣을 포인트 목록. [point_id] 형태로 넣어야
    # LLM이 target_point_id 필드에 정확한 id를 그대로 사용할 수 있다.
    lines = []
    for p in points:
        lines.append(f"- [{p.point_id}] {p.title}: {p.detail}")
    return "\n".join(lines)


def generate_review(state: dict) -> dict:
    """Send로 파견된 노드. sub-state 구조: {reviewer, target_opinion, brief, slot}

    slot: "a"면 review_a, "b"면 review_b 키로 반환.
    두 노드가 서로 다른 키에 쓰므로 병렬 실행해도 충돌이 없다.
    """
    reviewer: TargetUserPersonaCard = state["reviewer"]
    target: Opinion = state["target_opinion"]
    brief: ServicePlanInput = state["brief"]
    slot: str = state["slot"]  # "a" 또는 "b"

    chain = _PROMPT | _llm
    # LLM은 _ReviewDraft(텍스트 필드만) 반환
    draft: _ReviewDraft = chain.invoke({
        "display_name": reviewer.display_name,
        "one_line_summary": reviewer.one_line_summary,
        "life_context": reviewer.life_context,
        "user_goals": "\n".join(f"- {g}" for g in reviewer.user_goals),
        "pain_points": "\n".join(f"- {p}" for p in reviewer.pain_points),
        "positive_triggers": "\n".join(f"- {t}" for t in reviewer.positive_triggers),
        "negative_triggers": "\n".join(f"- {t}" for t in reviewer.negative_triggers),
        "speaking_style": reviewer.speaking_style,
        "guardrails": "\n".join(f"- {g}" for g in reviewer.guardrails),
        "title": brief.title or "",
        "description": brief.description or "",
        "target_persona_id": target.persona_id,
        "positive_points": _format_points(target.positive_points),
        "negative_points": _format_points(target.negative_points),
        "would_use": "사용할 것" if target.would_use else "사용 안 할 것",
        "would_use_description": target.would_use_description or "",
    })

    # LLM 결과(draft) + 코드에서 주입하는 id 필드를 합쳐 최종 Review 객체 생성
    review = Review(
        reviewer_id=reviewer.card_id,   # 리뷰 작성자 id
        target_id=target.persona_id,    # 리뷰 대상(상대방) id
        point_feedbacks=[
            PointFeedback(
                target_point_id=pf.target_point_id,
                agreement=pf.agreement,
                comment=pf.comment,
            )
            for pf in draft.point_feedbacks
        ],
        overall_comment=draft.overall_comment,
        revised_would_use=draft.revised_would_use,
    )

    # slot이 "a"면 state["review_a"], "b"면 state["review_b"]에 저장.
    return {f"review_{slot}": review}
