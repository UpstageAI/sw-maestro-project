"""LangGraph 노드 정의. 담당: C(이유준).

ReAct 패턴: 1) 일정 확인 → 2) 건강 확인 → 3) 운동 기록 확인 → 스케줄 도출.
외부 LLM 호출은 이 파일 안에 모은다(다른 모듈에서 직접 OpenAI 호출 금지).
"""
from __future__ import annotations

import datetime
import json
import os
from collections.abc import AsyncIterator

from pydantic import BaseModel

from schemas.models import ScheduleProposal, WorkoutSlot


class _SlotsOnly(BaseModel):
    """refine_node 전용 — LLM이 slots만 생성하고 fatigue_timeline은 Python이 복원한다."""
    slots: list[WorkoutSlot]

_REACT_STEPS = ["get_calendar", "get_health", "get_workouts"]

_DOW_KEYWORDS: dict[str, int] = {
    "월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3,
    "금요일": 4, "토요일": 5, "일요일": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6,
}
_DOW_NAMES = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def _resolve_target_date(text: str) -> tuple[datetime.date, str] | tuple[None, None]:
    """사용자 입력에서 요일 키워드를 찾아 이번 주 해당 날짜와 요일명을 반환한다.

    긴 키워드(예: '월요일')를 먼저 매칭해 '월', '화' 같은 단일 문자가 잘못 매칭되는 일을 막는다.
    """
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    text_lower = text.lower()
    for kw in sorted(_DOW_KEYWORDS, key=len, reverse=True):
        if kw in text_lower:
            weekday = _DOW_KEYWORDS[kw]
            target = week_start + datetime.timedelta(days=weekday)
            return target, _DOW_NAMES[weekday]
    return None, None


def _this_week_range() -> tuple[str, str]:
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday())
    end = start + datetime.timedelta(days=6)
    return start.isoformat(), end.isoformat()


# ── 노드 함수 ────────────────────────────────────────────────────────────────

def think_node(state: dict) -> dict:
    """다음에 호출할 Tool을 결정한다.

    mode=="refine"이면 refine 노드로 보내고,
    그 외에는 get_calendar → get_health → get_workouts → compose 고정 순서로 진행.
    """
    if state.get("mode") == "refine":
        return {"next_action": "refine"}

    called: list[str] = state.get("tools_called", [])
    for step in _REACT_STEPS:
        if step not in called:
            return {"next_action": step}
    return {"next_action": "compose"}


def call_tool_node(state: dict) -> dict:
    """next_action에 해당하는 Tool을 호출하고 결과를 state에 저장한다."""
    from agent.tools import calendar_tool, health_tool, workouts_tool

    action: str = state["next_action"]
    start, end = _this_week_range()
    called: list[str] = list(state.get("tools_called", []))

    if action == "get_calendar":
        data = calendar_tool.invoke({"start": start, "end": end})
        called.append("get_calendar")
        return {"calendar_data": data, "tools_called": called}

    if action == "get_health":
        data = health_tool.invoke({"start": start, "end": end})
        called.append("get_health")
        return {"health_data": data, "tools_called": called}

    if action == "get_workouts":
        data = workouts_tool.invoke({"start": start, "end": end})
        called.append("get_workouts")
        return {"workouts_data": data, "tools_called": called}

    return {}


async def compose_schedule_node(state: dict) -> dict:
    """수집한 데이터를 LLM에 전달해 이번 주 ScheduleProposal을 생성한다."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    from agent.prompts import COMPOSE_PROMPT, SYSTEM_PROMPT

    calendar: list[dict] = state.get("calendar_data", [])
    health: list[dict] = state.get("health_data", [])
    workouts: list[dict] = state.get("workouts_data", [])
    user_input: str = state.get("user_input", "")

    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    # datetime/date 필드가 포함돼 있어 strict JSON schema 모드가 거부함 → function_calling 사용
    structured_llm = llm.with_structured_output(ScheduleProposal, method="function_calling")

    prompt = COMPOSE_PROMPT.format(
        today=today.isoformat(),
        week_start=week_start.isoformat(),
        user_input=user_input,
        calendar_json=json.dumps(calendar, ensure_ascii=False),
        health_json=json.dumps(health, ensure_ascii=False),
        workouts_json=json.dumps(workouts, ensure_ascii=False),
    )

    proposal: ScheduleProposal = await structured_llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    return {"proposal": proposal.model_dump(mode="json")}


async def refine_node(state: dict) -> dict:
    """멀티턴 재조정 노드. 사용자 피드백을 LLM에 전달해 해당 날짜 슬롯만 교체한다."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    from agent.prompts import REFINE_SCHEDULE_PROMPT, SYSTEM_PROMPT

    proposal_dict = state.get("proposal")
    if not proposal_dict:
        return {}

    user_input: str = state.get("user_input", "")
    calendar: list[dict] = state.get("calendar_data", [])

    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    weekday_map = "\n".join(
        f"  {_DOW_NAMES[i]}: {(week_start + datetime.timedelta(days=i)).isoformat()}"
        for i in range(7)
    )

    # Python에서 요일→날짜 해석. LLM에 최종 날짜를 직접 알려줘 계산 오류 방지.
    target_date, target_dow = _resolve_target_date(user_input)
    if target_date is not None:
        target_date_hint = f"{target_date.isoformat()} ({target_dow}) ← 이 날짜의 슬롯만 변경"
    else:
        target_date_hint = "미지정 — 피드백에서 날짜를 판단하여 변경"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    # LLM에는 slots만 요청 — fatigue_timeline은 LLM이 빠뜨리는 경우가 잦으므로 Python에서 복원
    structured_llm = llm.with_structured_output(_SlotsOnly, method="function_calling")

    # slots만 담은 proposal JSON (fatigue_timeline 제거 → 불필요한 복사 혼동 방지)
    slots_only_json = json.dumps({"slots": proposal_dict.get("slots", [])}, ensure_ascii=False)

    prompt = REFINE_SCHEDULE_PROMPT.format(
        today=today.isoformat(),
        today_dow=_DOW_NAMES[today.weekday()],
        weekday_map=weekday_map,
        target_date_hint=target_date_hint,
        user_feedback=user_input,
        current_proposal_json=slots_only_json,
        calendar_json=json.dumps(calendar, ensure_ascii=False),
    )

    result: _SlotsOnly = await structured_llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    # fatigue_timeline은 원본에서 그대로 복원
    original = ScheduleProposal.model_validate(proposal_dict)
    updated = ScheduleProposal(slots=result.slots, fatigue_timeline=original.fatigue_timeline)
    return {"proposal": updated.model_dump(mode="json")}


def _format_slots(slots: list[dict]) -> str:
    """슬롯 목록을 LLM 프롬프트용 텍스트로 변환한다."""
    lines = []
    for s in slots:
        date_str = s["start"][:10]
        time_str = f"{s['start'][11:16]}~{s['end'][11:16]}"
        muscles = ", ".join(s.get("target_muscles", []))
        rationale = s.get("rationale", "")
        lines.append(f"- {date_str} {time_str}: {s['type']} ({muscles}) — {rationale}")
    return "\n".join(lines)


async def generate_proposal_summary(
    proposal: dict,
    user_input: str,
    api_key: str,
    is_refine: bool = False,
    prior_proposal: dict | None = None,
) -> AsyncIterator[str]:
    """제안된 스케줄을 한국어 텍스트로 토큰 단위로 스트리밍한다. LLM 호출은 이 파일에만.

    is_refine=True + prior_proposal 제공 시 REFINE_PROMPT로 실제 변경 내용을 설명한다 (F6 AC3).
    schemas/CLAUDE.md: text 청크는 "LLM 토큰 단위 응답 (delta 누적은 FE가 처리)".
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    from agent.prompts import REFINE_PROMPT, SYSTEM_PROMPT

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=api_key)

    current_text = _format_slots(proposal.get("slots", []))

    if is_refine and prior_proposal is not None:
        previous_text = _format_slots(prior_proposal.get("slots", []))
        prompt = REFINE_PROMPT.format(
            user_feedback=user_input,
            previous_proposal=previous_text,
            updated_proposal=current_text,
        )
    else:
        prompt = (
            f"사용자 요청: {user_input}\n\n"
            f"이번 주 운동 스케줄:\n{current_text}\n\n"
            "위 스케줄을 따뜻하고 격려하는 톤으로 2~3문장으로 소개해 주세요. 한국어로."
        )

    async for chunk in llm.astream([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]):
        yield chunk.content
