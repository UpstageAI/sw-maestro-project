"""Agent 6 — Response Generation (LangGraph node).

Builds the final user-facing payload: saju-grounded headline + styleReason +
per-destination reason map. This node also emits the terminal
``pipeline_done`` event.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from langgraph.config import get_stream_writer

from _lib.bazi import ELEMENT_TRAVEL_AFFINITY
from _lib.solar import ChatMessage, SolarOptions, call_solar_json
from _lib.state import AgentState, make_event
from _lib.travel_styles import TRAVEL_STYLES

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 사주 명리학 기반 여행 추천 큐레이터입니다.
사용자에게 보여줄 결과 페이지 상단 카피를 작성합니다.
규칙:
- headline: 한 줄 요약. 어떤 오행이 강하고 어떤 오행이 부족한지를 자연스럽게 언급. 30자 이내 권장.
- styleReason: 2~3문장. 추천된 여행 스타일이 부족한 오행을 어떻게 보완하는지 설명. 사주 해석을 반드시 포함.
- 단정적인 점괘가 아니라 "결이 보여요", "흐름이에요" 같은 부드러운 어조.
- 출력은 반드시 단일 JSON 객체. {"headline":"...","styleReason":"..."}"""


def _fallback_headline(saju: Dict[str, Any]) -> str:
    strong = saju["elements"]["strong"][0] if saju["elements"]["strong"] else saju["elements"]["dominant"]
    return (
        f"{strong}({strong}) 기운이 강해 {saju['needsBoost']}({saju['needsBoost']}) "
        "보완이 필요한 결의 시기예요."
    )


def _fallback_style_reason(saju: Dict[str, Any], mapping: Dict[str, Any]) -> str:
    env = "/".join(ELEMENT_TRAVEL_AFFINITY[saju["needsBoost"]]["environments"][:2])
    primary_label = TRAVEL_STYLES[mapping["primary"]]["label"]
    return (
        f"{saju['elements']['dominant']}({saju['elements']['dominant']})이 강한 흐름이라, "
        f"부족한 {saju['needsBoost']}({saju['needsBoost']})을 {env} 같은 환경으로 채워 주는 "
        f"{primary_label} 결이 잘 어울립니다."
    )


async def _fetch_headline(
    saju: Dict[str, Any],
    mapping: Dict[str, Any],
    ranked: List[Dict[str, Any]],
    api_key: str,
    model: str | None,
) -> Dict[str, str]:
    strong_str = ", ".join(saju["elements"]["strong"]) or "뚜렷하지 않음"
    weak_str = ", ".join(saju["elements"]["weak"]) or "뚜렷하지 않음"
    primary_label = TRAVEL_STYLES[mapping["primary"]]["label"]
    style_str = (
        f"{primary_label} + {TRAVEL_STYLES[mapping['secondary']]['label']}"
        if mapping["secondary"] else primary_label
    )
    top_names = ", ".join(r["destination"]["name"] for r in ranked)

    user_prompt = "\n".join([
        f"일간: {saju['chart']['dayMaster']['stem']}({saju['chart']['dayMaster']['element']})",
        f"강한 오행: {strong_str}",
        f"부족한 오행: {weak_str}",
        f"보완이 필요한 오행: {saju['needsBoost']}",
        f"매핑 스타일: {style_str}",
        f"상위 3 여행지: {top_names}",
        "",
        "위 정보를 바탕으로 결과 화면 헤드라인과 스타일 이유를 작성해 주세요.",
    ])

    try:
        res = await call_solar_json(
            [
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ],
            SolarOptions(api_key=api_key, model=model, temperature=0.5, max_tokens=400),
        )
        if isinstance(res, dict):
            return {
                "headline": res.get("headline") or _fallback_headline(saju),
                "styleReason": res.get("styleReason") or _fallback_style_reason(saju, mapping),
            }
    except Exception as err:  # noqa: BLE001
        logger.warning("[responseGeneration] Solar fallback: %s", err)

    return {
        "headline": _fallback_headline(saju),
        "styleReason": _fallback_style_reason(saju, mapping),
    }


async def response_generation_node(state: AgentState) -> Dict[str, Any]:
    writer = get_stream_writer()
    writer(make_event(
        "agent_start", agent="response-generation", index=5, total=6,
    ))

    saju = state["saju"]
    mapping = state["mapping"]
    ranked = state["ranked"]
    api_key = state["apiKey"]
    model = state.get("model")

    selected_styles: List[str] = (
        [mapping["primary"], mapping["secondary"]] if mapping["secondary"] else [mapping["primary"]]
    )

    reasons_by_destination: Dict[str, str] = {
        r["destination"]["id"]: r["reason"] for r in ranked
    }

    llm = await _fetch_headline(saju, mapping, ranked, api_key, model)

    result: Dict[str, Any] = {
        "saju": saju,
        "styleMapping": mapping,
        "ranked": ranked,
        "selectedStyles": selected_styles,
        "styleReason": llm["styleReason"],
        "reasonsByDestination": reasons_by_destination,
        "headline": llm["headline"],
    }

    writer(make_event(
        "agent_done", agent="response-generation", index=5, total=6,
        payload={"headline": result["headline"]},
    ))
    writer(make_event("pipeline_done", payload=result))

    return {"result": result}
