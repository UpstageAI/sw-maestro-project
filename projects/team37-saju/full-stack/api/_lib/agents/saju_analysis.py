"""Agent 2 — Saju Analysis (LangGraph node).

Deterministic Bazi calculation seeds an element balance; Solar then turns the
chart into a personality / yearly-energy narrative. Falls back to a chart-
grounded narrative when Solar fails so the pipeline keeps running.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.config import get_stream_writer

from _lib.bazi import (
    ELEMENT_TRAVEL_AFFINITY,
    Element,
    compute_bazi,
    compute_element_balance,
)
from _lib.solar import ChatMessage, SolarOptions, call_solar_json
from _lib.state import AgentState, make_event

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 한국 전통 사주 명리학에 능통한 분석가입니다.
주어진 사주 차트(년/월/일/시 천간·지지)와 오행 분포를 바탕으로
사용자의 성향과 현재 운세 흐름을 짧은 한국어로 요약해 주세요.

규칙:
- 모든 해석은 반드시 입력된 차트와 오행 수치에 근거해야 합니다.
- 사용자에게 운명이나 단정적인 예언을 하지 마세요. "~한 결", "~한 시기"처럼 결을 묘사합니다.
- "재미·참고용"이라는 면책에 어긋나지 않도록 부드러운 어조를 유지합니다.
- 출력은 반드시 단일 JSON 객체로만 응답하세요. 코드 펜스, 주석 금지."""


def _pick_needs_boost(balance: Dict[str, Any]) -> Element:
    if balance["weak"]:
        return balance["weak"][0]
    # 상극: 목→금, 화→수, 토→목, 금→화, 수→토 (controller of dominant)
    controller: Dict[Element, Element] = {
        "목": "금", "화": "수", "토": "목", "금": "화", "수": "토",
    }
    return controller[balance["dominant"]]


def _build_user_prompt(
    user_input: Dict[str, Any],
    balance: Dict[str, Any],
    day_master: Dict[str, str],
    needs_boost: Element,
) -> str:
    element_line = ", ".join(
        f"{k}: {balance['scores'][k]:.1f}" for k in ["목", "화", "토", "금", "수"]
    )
    strong_str = ", ".join(balance["strong"]) or "없음"
    weak_str = ", ".join(balance["weak"]) or "없음"
    return "\n".join([
        f"생년월일: {user_input['birthDate']}",
        f"태어난 시: {user_input['birthHour']}",
        f"일간(자기 자신): {day_master['stem']}({day_master['element']})",
        f"오행 분포: {element_line}",
        f"강한 오행: {strong_str}",
        f"부족한 오행: {weak_str}",
        f"보완이 필요한 오행: {needs_boost}",
        "",
        "아래 JSON 스키마로만 응답해주세요:",
        """{
  "personalityKeywords": string[3~5],
  "yearlyEnergy": string,
  "narrative": string
}""",
        "",
        '예시 어조: "화(火) 기운이 강해 활동적이고 개방적인 공간이 잘 맞아요. 다만 수(水)가 부족해 마음이 가라앉을 시간이 필요한 시기예요."',
    ])


def _fallback_narrative(
    balance: Dict[str, Any],
    day_master: Dict[str, str],
    needs_boost: Element,
) -> Dict[str, Any]:
    dominant_traits = ELEMENT_TRAVEL_AFFINITY[balance["dominant"]]["keywords"]
    boost_envs = ELEMENT_TRAVEL_AFFINITY[needs_boost]["environments"]
    return {
        "personalityKeywords": dominant_traits[:3],
        "yearlyEnergy": (
            f"{needs_boost}({needs_boost}) 기운의 보완이 필요한 결의 시기로, "
            f"{boost_envs[0]} 가까이에서 호흡을 가다듬으면 좋아요."
        ),
        "narrative": (
            f"일간이 {day_master['stem']}({day_master['element']})으로, "
            f"{balance['dominant']} 기운이 두드러지는 분이에요. "
            f"{balance['dominant']}의 결이 강해 {dominant_traits[0]} 성향이 자연스럽게 "
            f"드러나지만, {needs_boost}이(가) 부족해 균형을 맞출 환경이 필요합니다."
        ),
    }


async def saju_analysis_node(state: AgentState) -> Dict[str, Any]:
    writer = get_stream_writer()
    writer(make_event(
        "agent_start", agent="saju-analysis", index=1, total=6,
    ))

    user_input = state["userInput"]
    api_key = state["apiKey"]
    model = state.get("model")

    chart = compute_bazi(user_input["birthDate"], user_input["birthHour"])
    elements = compute_element_balance(chart)
    needs_boost = _pick_needs_boost(elements)

    messages: list[ChatMessage] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_prompt(user_input, elements, chart["dayMaster"], needs_boost),
        },
    ]

    try:
        llm = await call_solar_json(
            messages,
            SolarOptions(api_key=api_key, model=model, temperature=0.4, max_tokens=600),
        )
        if not isinstance(llm, dict):
            llm = _fallback_narrative(elements, chart["dayMaster"], needs_boost)
    except Exception as err:  # noqa: BLE001 — fallback like the TS version
        logger.warning("[sajuAnalysis] Solar fallback used: %s", err)
        llm = _fallback_narrative(elements, chart["dayMaster"], needs_boost)

    saju: Dict[str, Any] = {
        "chart": chart,
        "elements": elements,
        "personalityKeywords": llm.get("personalityKeywords") or [],
        "yearlyEnergy": llm.get("yearlyEnergy") or "",
        "needsBoost": needs_boost,
        "narrative": llm.get("narrative") or "",
    }

    writer(make_event(
        "agent_done", agent="saju-analysis", index=1, total=6,
        payload={
            "dayMaster": chart["dayMaster"],
            "elements": elements["scores"],
            "needsBoost": needs_boost,
        },
    ))

    return {"saju": saju}
