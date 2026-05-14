"""f1_select — 100개 카드 풀에서 LLM이 2명을 선정하고 근거를 함께 반환."""

import sys

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from langgraph.types import Send

from schemas import (
    PersonaSelectionReason,
    ServicePlanInput,
    TargetUserPersonaCard,
)
from services.persona_repository import load_personas
from services.persona_retrieval import rank_personas_for_brief
from state import ProjectState

load_dotenv()

_SELECT_COUNT = 2
_RETRIEVAL_POOL_LIMIT = 30
_LLM_TIMEOUT_SECONDS = 120.0
_LLM_MAX_RETRIES = 5
_LLM_FAILURE_PAIR_REASON = "LLM 호출 실패 - 풀 앞 2개로 fallback"


_llm = ChatUpstage(
    model="solar-pro3",
    timeout=_LLM_TIMEOUT_SECONDS,
    max_retries=_LLM_MAX_RETRIES,
).with_structured_output(PersonaSelectionReason)


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 서비스 기획안 검토를 위해 서로 보완적인 관점을 가진 페르소나 패널 "
        f"{_SELECT_COUNT}명을 선정합니다.\n\n"
        "선정 기준 (순서 = 우선순위):\n"
        "1) 기획안에 명시된 타겟의 demographic(연령대, 직업, 지역, 가족 맥락)을 "
        "충실히 반영합니다. 명시된 demographic 조건을 충족하는 카드를 우선 후보로 고려하세요.\n"
        "2) 잠재 리스크 검증, 기획안의 우려사항과 약점을 가장 잘 드러낼 페르소나를 고릅니다.\n"
        "3) 두 사람의 관점 차이, 같은 demographic 조건 안에서 서로 다른 직업, 생활맥락, "
        "트리거를 가진 페어를 선호합니다. 단, 1)의 타겟 적합성보다 앞세우지 마세요.\n\n"
        "후보 목록은 기획안과의 semantic relevance가 높은 순서로 정렬되어 있습니다. "
        "상위 후보를 우선 검토하고, 하위 후보는 상위 후보가 타겟/리스크 검증에 명백히 부적합할 때만 선택하세요. "
        "두 명 중 최소 한 명은 기획안의 핵심 타겟과 직접 일치해야 합니다. "
        "선정 근거는 후보 목록에 적힌 사실만 사용하고 지역/직업/생활맥락을 추측하지 마세요.\n\n"
        "페어 구성 계약:\n"
        "- Anchor/Complement는 내부 선택 역할입니다. 이 역할명은 출력 본문에 그대로 쓰지 마세요.\n"
        "- selected_card_ids[0]은 Anchor입니다. Anchor는 기획안의 핵심 타겟과 가장 직접적으로 일치해야 합니다.\n"
        "- selected_card_ids[1]은 Complement입니다. Complement는 Anchor와 같은 서비스 문제 공간 안에 있으면서, "
        "Anchor와 다른 사용 맥락, 이해관계, 리스크를 제공해야 합니다.\n"
        "- Complement는 단순히 산업/키워드가 비슷한 후보보다, 실제 서비스 흐름에서 다른 검증 관점을 주는 후보를 우선합니다.\n"
        "- 두 사람 사이의 공유 연결고리 1개와 서로 다른 검증 관점 1개를 후보 목록의 사실로 설명할 수 없으면 그 조합은 선택하지 마세요.\n\n"
        "출력 규칙:\n"
        "- selected_card_ids 는 반드시 아래 후보 목록에 실재하는 card_id 정확히 2개입니다.\n"
        "- per_persona_reasons 는 비우지 말고 선택한 두 card_id 각각에 대해 한 줄을 작성합니다.\n"
        "- pair_reason 은 두 사람의 공유 연결고리와 서로 다른 검증 관점을 후보 목록의 사실에 근거해 서술합니다. "
        "카드 이름과 card_id 는 쓰지 말고, 직업/생활맥락을 왜곡하거나 새로 만들지 마세요.\n"
        "- expected_review_angles 는 비우지 말고 짧은 명사구 3~5개로 작성합니다.",
    ),
    (
        "human",
        "## 서비스 기획안\n"
        "제목: {title}\n"
        "타겟: {target}\n"
        "설명: {description}\n"
        "핵심 기능:\n{key_features}\n"
        "우려사항: {concerns}\n\n"
        "## 페르소나 후보 ({pool_size}명)\n{persona_list}",
    ),
])


def _format_persona_list(pool: list[TargetUserPersonaCard]) -> str:
    """LLM 프롬프트에 들어갈 압축 카드 목록.

    선택 판단의 핵심 필드(요약, 생활맥락, 목표, 불편함, 트리거)를 포함한다.
    speaking_style/guardrails/source_uuid는 의도적으로 제외.
    """
    lines = []
    for card in pool:
        parts = [
            f"- card_id: {card.card_id}",
            "  이름/메타: "
            + " | ".join([
                card.display_name,
                card.age_group or "-",
                card.sex or "-",
                card.occupation or "-",
                card.region or "-",
            ]),
            f"  요약: {card.one_line_summary}",
            f"  생활맥락: {card.life_context}",
            "  목표: " + " / ".join(card.user_goals) if card.user_goals else "  목표: -",
            "  불편함: " + " / ".join(card.pain_points) if card.pain_points else "  불편함: -",
            "  긍정 트리거: " + " / ".join(card.positive_triggers) if card.positive_triggers else "  긍정 트리거: -",
            "  부정 트리거: " + " / ".join(card.negative_triggers) if card.negative_triggers else "  부정 트리거: -",
        ]
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def _resolve_selection(
    raw_ids: list[str],
    pool: list[TargetUserPersonaCard],
) -> list[TargetUserPersonaCard]:
    """LLM이 반환한 id 목록을 풀과 매칭해 정확히 _SELECT_COUNT 개로 만든다."""
    by_id = {card.card_id: card for card in pool}
    selected: list[TargetUserPersonaCard] = []
    seen: set[str] = set()

    for card_id in raw_ids:
        if card_id in by_id and card_id not in seen:
            selected.append(by_id[card_id])
            seen.add(card_id)
            if len(selected) == _SELECT_COUNT:
                return selected

    for card in pool:
        if card.card_id not in seen:
            selected.append(card)
            seen.add(card.card_id)
            if len(selected) == _SELECT_COUNT:
                return selected

    return selected


def _llm_select(
    brief: ServicePlanInput,
    pool: list[TargetUserPersonaCard],
) -> PersonaSelectionReason:
    chain = _PROMPT | _llm
    return chain.invoke({
        "title": brief.title or "",
        "target": brief.target or "",
        "description": brief.description or "",
        "key_features": "\n".join(f"- {f}" for f in brief.key_features),
        "concerns": brief.concerns or "",
        "pool_size": len(pool),
        "persona_list": _format_persona_list(pool),
    })


def _result(
    selected: list[TargetUserPersonaCard],
    reason: PersonaSelectionReason,
) -> dict:
    return {
        "persona_a": selected[0],
        "persona_b": selected[1],
        "persona_selection_reason": reason,
    }


def _normalize_reason(
    reason: PersonaSelectionReason,
    selected: list[TargetUserPersonaCard],
) -> PersonaSelectionReason:
    selected_ids = [card.card_id for card in selected]
    per_persona_reasons = {
        card_id: reason.per_persona_reasons.get(card_id) or "후보 목록 기준으로 선택됨"
        for card_id in selected_ids
    }
    return reason.model_copy(
        update={
            "selected_card_ids": selected_ids,
            "per_persona_reasons": per_persona_reasons,
        }
    )


def select_personas(state: ProjectState) -> dict:
    brief: ServicePlanInput = state["brief"]
    pool = rank_personas_for_brief(brief, load_personas())[:_RETRIEVAL_POOL_LIMIT]

    if len(pool) <= _SELECT_COUNT:
        selected = list(pool)[:_SELECT_COUNT]
        reason = PersonaSelectionReason(
            selected_card_ids=[c.card_id for c in selected],
            pair_reason="풀 크기가 부족해 전원 선택",
        )
        return _result(selected, reason)

    try:
        reason = _llm_select(brief, pool)
    except Exception as exc:
        print(
            f"[f1_select] LLM 호출 실패, 풀 앞 2개로 fallback: {exc!r}",
            file=sys.stderr,
            flush=True,
        )
        selected = list(pool[:_SELECT_COUNT])
        fallback_reason = PersonaSelectionReason(
            selected_card_ids=[c.card_id for c in selected],
            pair_reason=_LLM_FAILURE_PAIR_REASON,
        )
        return _result(selected, fallback_reason)

    selected = _resolve_selection(reason.selected_card_ids, pool)
    normalized_reason = _normalize_reason(reason, selected)
    return _result(selected, normalized_reason)


def route_opinions(state: ProjectState) -> list[Send]:
    """선택된 두 페르소나에 대해 generate_opinion 노드를 병렬 파견."""
    return [
        Send("generate_opinion", {"persona": state["persona_a"], "brief": state["brief"], "slot": "a"}),
        Send("generate_opinion", {"persona": state["persona_b"], "brief": state["brief"], "slot": "b"}),
    ]
