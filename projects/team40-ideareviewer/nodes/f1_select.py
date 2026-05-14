"""f1_select — 기획안 타겟에 맞는 페르소나 선택 + 병렬 의견 생성 Send 파견."""

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from langgraph.types import Send
from pydantic import BaseModel, Field

from schemas import ServicePlanInput, TargetUserPersonaCard
from services.persona_repository import load_personas
from state import ProjectState

load_dotenv()

_SELECT_COUNT = 2


# LLM에게 card_id 목록만 고르게 한다.
# 전체 카드 객체를 반환하게 하면 LLM이 내용을 임의로 변형할 수 있으므로
# id만 받고 실제 객체는 코드에서 직접 매핑한다.
class _Selection(BaseModel):
    selected_card_ids: list[str] = Field(
        description=f"타겟에 가장 적합한 페르소나 card_id {_SELECT_COUNT}개"
    )


_llm = ChatUpstage(model="solar-pro3").with_structured_output(_Selection)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 서비스 기획안의 타겟 유저에 맞는 페르소나를 선정하는 전문가입니다. "
        f"아래 페르소나 목록에서 기획안 타겟에 가장 적합한 {_SELECT_COUNT}명을 선택하세요. "
        "card_id만 반환하면 됩니다.",
    ),
    (
        "human",
        "## 서비스 기획안\n"
        "제목: {title}\n"
        "타겟: {target}\n"
        "핵심 기능: {key_features}\n\n"
        "## 페르소나 목록\n{persona_list}",
    ),
])


def _format_persona_list(pool: list[TargetUserPersonaCard]) -> str:
    # LLM 프롬프트에 넣을 페르소나 목록 텍스트. card_id를 명시해야 LLM이 선택 결과를 id로 반환한다.
    # source_uuid(내부 ID)·guardrails(응답 메타 지침)는 선택 기준과 무관하므로 제외.
    lines = []
    for p in pool:
        parts = [
            f"- card_id: {p.card_id}",
            f"  이름: {p.display_name} | 연령대: {p.age_group or '-'} | 성별: {p.sex or '-'} | 직업: {p.occupation or '-'} | 지역: {p.region or '-'}",
            f"  요약: {p.one_line_summary}",
            f"  생활 맥락: {p.life_context}",
        ]
        if p.user_goals:
            parts.append("  목표: " + " / ".join(p.user_goals))
        if p.pain_points:
            parts.append("  불편사항: " + " / ".join(p.pain_points))
        if p.positive_triggers:
            parts.append("  긍정 반응: " + " / ".join(p.positive_triggers))
        if p.negative_triggers:
            parts.append("  부정 반응: " + " / ".join(p.negative_triggers))
        parts.append(f"  말투: {p.speaking_style}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def _llm_select(brief: ServicePlanInput, pool: list[TargetUserPersonaCard]) -> list[TargetUserPersonaCard]:
    chain = _PROMPT | _llm
    result: _Selection = chain.invoke({
        "title": brief.title or "",
        "target": brief.target or "",
        "key_features": "\n".join(f"- {f}" for f in brief.key_features),
        "persona_list": _format_persona_list(pool),
    })
 
    # LLM이 반환한 card_id → 실제 카드 객체로 변환
    id_set = {p.card_id: p for p in pool}
    selected = [id_set[cid] for cid in result.selected_card_ids if cid in id_set]

    # LLM이 존재하지 않는 id를 반환했을 경우 앞에서부터 채움
    if len(selected) < _SELECT_COUNT:
        fallback = [p for p in pool if p not in selected]
        selected += fallback[:_SELECT_COUNT - len(selected)]

    return selected[:_SELECT_COUNT]


def select_personas(state: ProjectState) -> dict:
    # f0_parse가 state["brief"]를 채워놨으므로 여기서 꺼내 쓴다.
    brief: ServicePlanInput = state["brief"]
    pool = load_personas()  # persona_cards.seed.json 전체 로드

    if len(pool) <= _SELECT_COUNT:
        # 풀이 적으면 LLM 호출 없이 전원 선택
        selected = pool
    else:
        selected = _llm_select(brief, pool)

    # state.py의 persona_a, persona_b 필드에 각각 매핑.
    # 리스트 대신 명시적 키를 쓰므로 Annotated 리듀서 없이도 충돌 없이 저장된다.
    return {"persona_a": selected[0], "persona_b": selected[1]}


def route_opinions(state: ProjectState) -> list[Send]:
    """선택된 두 페르소나에 대해 generate_opinion 노드를 병렬 파견.

    LangGraph conditional edge에 등록되는 함수.
    list[Send]를 반환하면 LangGraph가 각 Send를 별도 실행 단위로 병렬 처리한다.

    slot="a"/"b"를 sub-state에 포함해서 넘긴다.
    generate_opinion은 이 slot 값을 보고 반환 키를 "opinion_a" 또는 "opinion_b"로 결정한다.
    두 노드가 서로 다른 키에 쓰기 때문에 Annotated 리듀서 없이도 충돌이 없다.
    """
    return [
        Send("generate_opinion", {"persona": state["persona_a"], "brief": state["brief"], "slot": "a"}),
        Send("generate_opinion", {"persona": state["persona_b"], "brief": state["brief"], "slot": "b"}),
    ]
