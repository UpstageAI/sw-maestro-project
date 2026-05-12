"""f2_opinion — 페르소나 의견 생성 + 교차 리뷰 Send 파견."""

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from langgraph.types import Send
from pydantic import BaseModel, Field

from schemas import Opinion, ReactionPoint, ServicePlanInput, TargetUserPersonaCard
from state import ProjectState

load_dotenv()


# LLM이 채울 필드만 정의한 중간 모델.
# schemas.py의 ReactionPoint에는 point_id가 있지만 LLM에게 id 생성을 맡기면
# 형식이 제멋대로가 되므로 title·detail만 받고 point_id는 코드에서 만든다.
class _ReactionPointDraft(BaseModel):
    title: str
    detail: str = Field(
        description="이 포인트에 대한 설명. 페르소나의 실제 삶과 연결해 2문장으로 간결하게 서술하세요."
    )


# 마찬가지로 schemas.py의 Opinion에는 persona_id가 있지만 LLM이 결정할 필요가 없다.
# LLM은 텍스트(포인트 내용·사용 의향)만 채우고, persona_id·point_id는 코드에서 주입.
class _OpinionDraft(BaseModel):
    """LLM이 생성할 의견 필드. persona_id·point_id는 코드에서 직접 설정."""

    positive_points: list[_ReactionPointDraft] = Field(
        description="긍정 포인트 3개. 각 detail은 2문장으로 간결하게 서술."
    )
    negative_points: list[_ReactionPointDraft] = Field(
        description="부정 포인트 3개. 각 detail은 2문장으로 간결하게 서술."
    )
    would_use: bool
    would_use_description: str = Field(
        description="사용 의향 이유. 3문장으로 간결하게 서술하세요."
    )


_llm = ChatUpstage(model="solar-pro3").with_structured_output(_OpinionDraft)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 아래 페르소나입니다. 반드시 이 페르소나의 시각과 말투로만 반응하세요.\n\n"
        "## 페르소나\n"
        "이름: {display_name}\n"
        "한 줄 요약: {one_line_summary}\n"
        "삶의 맥락: {life_context}\n"
        "목표: {user_goals}\n"
        "불편함: {pain_points}\n"
        "긍정 트리거: {positive_triggers}\n"
        "부정 트리거: {negative_triggers}\n"
        "말투: {speaking_style}\n\n"
        "## 작성 지침\n"
        "- 각 포인트의 detail은 2문장으로 간결하게, 페르소나의 실제 삶과 연결해 구체적으로 쓰세요.\n"
        "- 추상적인 표현 금지. '불편할 수 있다' 대신 '내가 흙 묻은 손으로 화면을 누르면...' 처럼 구체적 상황으로 쓰세요.\n"
        "- would_use_description은 3문장으로 간결하게 서술하세요.\n"
        "- 말투는 페르소나의 speaking_style을 반드시 반영하세요.\n\n"
        "## 준수사항\n{guardrails}",
    ),
    (
        "human",
        "## 서비스 기획안\n"
        "제목: {title}\n"
        "설명: {description}\n"
        "타겟: {target}\n"
        "핵심 기능:\n{key_features}\n"
        "우려사항: {concerns}\n\n"
        "위 서비스에 대해 긍정 포인트 3개, 부정 포인트 3개, 사용 의향을 작성해 주세요. "
        "각 포인트 detail은 2문장, would_use_description은 3문장으로 간결하게 써야 합니다.",
    ),
])


def generate_opinion(state: dict) -> dict:
    """Send로 파견된 노드. state는 ProjectState 전체가 아니라 Send에서 넘긴 sub-state.

    sub-state 구조: {"persona": TargetUserPersonaCard, "brief": ServicePlanInput, "slot": "a" | "b"}
    slot: route_opinions에서 넘긴 값. "a"면 opinion_a, "b"면 opinion_b 키로 반환.
    두 노드가 서로 다른 키에 쓰므로 충돌 없이 병렬 실행된다.
    """
    persona: TargetUserPersonaCard = state["persona"]
    brief: ServicePlanInput = state["brief"]
    slot: str = state["slot"]  # "a" 또는 "b"

    chain = _PROMPT | _llm
    # LLM은 _OpinionDraft(텍스트 필드만) 반환. id 관련 필드는 아직 없다.
    draft: _OpinionDraft = chain.invoke({
        "display_name": persona.display_name,
        "one_line_summary": persona.one_line_summary,
        "life_context": persona.life_context,
        "user_goals": "\n".join(f"- {g}" for g in persona.user_goals),
        "pain_points": "\n".join(f"- {p}" for p in persona.pain_points),
        "positive_triggers": "\n".join(f"- {t}" for t in persona.positive_triggers),
        "negative_triggers": "\n".join(f"- {t}" for t in persona.negative_triggers),
        "speaking_style": persona.speaking_style,
        "guardrails": "\n".join(f"- {g}" for g in persona.guardrails),
        "title": brief.title or "",
        "description": brief.description or "",
        "target": brief.target or "",
        "key_features": "\n".join(f"- {f}" for f in brief.key_features),
        "concerns": brief.concerns or "",
    })

    # card_id = "persona_01c6db49a3f2" → split("_")[1] = "01c6db49a3f2"
    # point_id를 "01c6db49a3f2_pos_01" 형태로 고정 규칙에 따라 생성.
    # LLM에게 id를 맡기지 않아야 f3에서 target_point_id로 참조할 때 일관성이 보장된다.
    prefix = persona.card_id.split("_")[1]
    opinion = Opinion(
        persona_id=persona.card_id,
        positive_points=[
            ReactionPoint(
                point_id=f"{prefix}_pos_{i + 1:02d}",
                title=p.title,
                detail=p.detail,
            )
            for i, p in enumerate(draft.positive_points)
        ],
        negative_points=[
            ReactionPoint(
                point_id=f"{prefix}_neg_{i + 1:02d}",
                title=p.title,
                detail=p.detail,
            )
            for i, p in enumerate(draft.negative_points)
        ],
        would_use=draft.would_use,
        would_use_description=draft.would_use_description,
    )

    # slot이 "a"면 state["opinion_a"], "b"면 state["opinion_b"]에 저장.
    # 다른 키에 쓰기 때문에 두 병렬 노드가 서로 덮어쓰지 않는다.
    return {f"opinion_{slot}": opinion}


def route_reviews(state: ProjectState) -> list[Send]:
    """collect_opinions(join) 이후 호출. opinion_a·opinion_b가 모두 채워진 뒤 교차 리뷰를 파견한다.

    교차 리뷰 규칙:
      - persona_a(slot="a")는 opinion_b를 리뷰
      - persona_b(slot="b")는 opinion_a를 리뷰
    """
    return [
        Send("generate_review", {
            "reviewer": state["persona_a"],
            "target_opinion": state["opinion_b"],  # A는 B의 의견을 리뷰
            "brief": state["brief"],
            "slot": "a",
        }),
        Send("generate_review", {
            "reviewer": state["persona_b"],
            "target_opinion": state["opinion_a"],  # B는 A의 의견을 리뷰
            "brief": state["brief"],
            "slot": "b",
        }),
    ]
