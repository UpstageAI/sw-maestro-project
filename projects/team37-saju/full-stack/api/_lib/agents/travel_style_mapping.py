"""Agent 3 — Travel Style Mapping (LangGraph node).

Deterministic scoring of the 6 internal travel styles against the saju
element balance + needsBoost; Solar generates the human-friendly rationale.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from langgraph.config import get_stream_writer

from _lib.solar import ChatMessage, SolarOptions, call_solar_json
from _lib.state import AgentState, make_event
from _lib.travel_styles import TRAVEL_STYLES

logger = logging.getLogger(__name__)

# StyleKey → preferred element weights.
STYLE_ELEMENT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "EMOTIONAL_RECOVERY": {"수": 3.0, "목": 1.5},
    "ENERGY_CHARGE": {"화": 3.0, "목": 1.0},
    "RELATIONSHIP_REFRESH": {"화": 2.0, "금": 1.5},
    "SELF_REFLECTION": {"목": 2.5, "토": 2.0},
    "ACTIVITY": {"화": 2.0, "목": 2.0},
    "CULTURE": {"토": 2.5, "금": 2.0},
}

# Tag preference per element — TravelStyle vocabulary.
ELEMENT_TO_TAGS: Dict[str, List[str]] = {
    "목": ["숲", "산", "사찰/한옥"],
    "화": ["핫플", "야경", "액티비티"],
    "토": ["사찰/한옥", "조용한 곳", "카페"],
    "금": ["전시/예술", "맛집", "카페"],
    "수": ["바다", "조용한 곳", "카페"],
}

SYSTEM_PROMPT = """당신은 사주 명리학과 여행 스타일을 잇는 매핑 전문가입니다.
주어진 오행 분포와 추천된 1~2개의 여행 스타일이 왜 잘 맞는지 한국어로 짧게 설명하세요.
출력은 반드시 JSON 객체 한 개로 합니다. {"rationale": "..."} 형식.
3~4문장 이내, 부족한 오행을 어떻게 보완하는지 반드시 언급하세요."""


def _score_styles(saju: Dict[str, Any]) -> Dict[str, Any]:
    style_scores: Dict[str, float] = {}
    elements_scores = saju["elements"]["scores"]
    needs_boost = saju["needsBoost"]
    for key, weights in STYLE_ELEMENT_WEIGHTS.items():
        s = 0.0
        for el, w in weights.items():
            element_score = elements_scores.get(el, 0)
            is_boost_target = el == needs_boost
            s += w * (1.5 if is_boost_target else 1.0) * (element_score / 5.0)
        style_scores[key] = s
    ordered = sorted(style_scores.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "primary": ordered[0][0],
        "secondary": ordered[1][0] if len(ordered) > 1 else None,
    }


def _unique_tags(tags: List[str]) -> List[str]:
    seen: Dict[str, None] = {}
    for t in tags:
        if t not in seen:
            seen[t] = None
    return list(seen.keys())


def _overlap_avoid_tags(strong: List[str], boost: str) -> List[str]:
    """If user is already strong in 화, avoid further 핫플/액티비티 — unless 화
    is also the boost target.
    """
    out: List[str] = []
    for el in strong:
        if el == boost:
            continue
        for t in ELEMENT_TO_TAGS.get(el, []):
            out.append(t)
    return _unique_tags(out)


async def travel_style_mapping_node(state: AgentState) -> Dict[str, Any]:
    writer = get_stream_writer()
    writer(make_event(
        "agent_start", agent="travel-style-mapping", index=2, total=6,
    ))

    saju = state["saju"]
    api_key = state["apiKey"]
    model = state.get("model")

    picked = _score_styles(saju)
    primary = picked["primary"]
    secondary = picked["secondary"]

    preferred_tags = _unique_tags(
        [
            *ELEMENT_TO_TAGS.get(saju["needsBoost"], []),
            *[t for el in saju["elements"]["strong"] for t in ELEMENT_TO_TAGS.get(el, [])][:2],
            *TRAVEL_STYLES[primary]["recommendKeywords"],
            *(TRAVEL_STYLES[secondary]["recommendKeywords"] if secondary else []),
        ]
    )

    avoid_tags: List[str] = (
        _overlap_avoid_tags(saju["elements"]["strong"], saju["needsBoost"])
        if saju["elements"]["strong"]
        else []
    )

    element_line = ", ".join(
        f"{k}={saju['elements']['scores'][k]:.1f}" for k in ["목", "화", "토", "금", "수"]
    )
    user_prompt = "\n".join([
        f"일간(자기): {saju['chart']['dayMaster']['stem']}({saju['chart']['dayMaster']['element']})",
        f"오행 분포: {element_line}",
        f"보완이 필요한 오행: {saju['needsBoost']}",
        f"1순위 스타일: {TRAVEL_STYLES[primary]['label']}",
        f"2순위 스타일: {TRAVEL_STYLES[secondary]['label'] if secondary else '없음'}",
        f"추천 태그: {', '.join(preferred_tags)}",
        "",
        "왜 이 스타일이 보완 오행과 맞물리는지 짧게 설명해 주세요.",
    ])

    rationale = ""
    try:
        res = await call_solar_json(
            [
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ],
            SolarOptions(api_key=api_key, model=model, temperature=0.4, max_tokens=350),
        )
        if isinstance(res, dict):
            rationale = res.get("rationale") or ""
    except Exception as err:  # noqa: BLE001
        logger.warning("[travelStyleMapping] Solar fallback: %s", err)

    if not rationale:
        rationale = (
            f"{saju['needsBoost']}({saju['needsBoost']}) 기운 보완이 필요한 시기라 "
            f"{TRAVEL_STYLES[primary]['label']}의 결이 잘 맞아요."
        )

    mapping: Dict[str, Any] = {
        "primary": primary,
        "secondary": secondary,
        "preferredTags": preferred_tags,
        "avoidTags": avoid_tags,
        "rationale": rationale,
    }

    writer(make_event(
        "agent_done", agent="travel-style-mapping", index=2, total=6,
        payload={"primary": primary, "secondary": secondary},
    ))

    return {"mapping": mapping}
