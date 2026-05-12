from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import AnalyzeScheduleResponse, ScheduleAnalysisContext, ScheduleCandidate
from app.services.ai_parser import ParsedSchedule, parse_schedule_text


class ScheduleGraphState(TypedDict, total=False):
    text: str
    timezone: str
    analysis_context: ScheduleAnalysisContext | None
    parsed: ParsedSchedule
    schedule: ScheduleCandidate
    missing_fields: list[str]
    needs_confirmation: bool
    next_analysis_context: ScheduleAnalysisContext
    message: str


def parse_schedule_node(state: ScheduleGraphState) -> dict[str, Any]:
    parsed = parse_schedule_text(
        state["text"],
        state["timezone"],
        state.get("analysis_context"),
    )
    return {"parsed": parsed}


def build_schedule_node(state: ScheduleGraphState) -> dict[str, Any]:
    parsed = state["parsed"]
    schedule = ScheduleCandidate(
        title=parsed.title,
        start_at=_parse_datetime(parsed.start_at),
        end_at=_parse_datetime(parsed.end_at),
        location=parsed.location,
        reminder_minutes=parsed.reminder_minutes,
        schedule_type=parsed.schedule_type,
    )
    missing_fields = _find_missing_fields(schedule)
    needs_confirmation = not missing_fields
    message = _build_message(missing_fields)
    next_analysis_context = _build_analysis_context(
        text=state["text"],
        timezone=state["timezone"],
        previous_context=state.get("analysis_context"),
        schedule=schedule,
        missing_fields=missing_fields,
    )

    return {
        "schedule": schedule,
        "missing_fields": missing_fields,
        "needs_confirmation": needs_confirmation,
        "next_analysis_context": next_analysis_context,
        "message": message,
    }


def analyze_schedule(
    text: str,
    timezone: str,
    analysis_context: ScheduleAnalysisContext | None = None,
) -> AnalyzeScheduleResponse:
    graph = _build_graph()
    result = graph.invoke(
        {"text": text, "timezone": timezone, "analysis_context": analysis_context}
    )
    next_analysis_context = result["next_analysis_context"]
    return AnalyzeScheduleResponse(
        original_text=next_analysis_context.original_text,
        schedule=result["schedule"],
        missing_fields=result["missing_fields"],
        needs_confirmation=result["needs_confirmation"],
        analysis_context=next_analysis_context,
        message=result["message"],
    )


def _build_graph():
    builder = StateGraph(ScheduleGraphState)
    builder.add_node("parse_schedule", parse_schedule_node)
    builder.add_node("build_schedule", build_schedule_node)
    builder.add_edge(START, "parse_schedule")
    builder.add_edge("parse_schedule", "build_schedule")
    builder.add_edge("build_schedule", END)
    return builder.compile()


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _find_missing_fields(schedule: ScheduleCandidate) -> list[str]:
    missing_fields: list[str] = []
    if not schedule.title:
        missing_fields.append("title")
    if not schedule.start_at:
        missing_fields.append("start_at")
    return missing_fields


def _build_message(missing_fields: list[str]) -> str:
    if "start_at" in missing_fields:
        return "일정을 등록하려면 날짜와 시간이 필요해요. 언제로 등록할까요?"
    if "title" in missing_fields:
        return "일정 제목을 확인해주세요."
    return "아래 일정으로 등록할까요?"


def _build_analysis_context(
    *,
    text: str,
    timezone: str,
    previous_context: ScheduleAnalysisContext | None,
    schedule: ScheduleCandidate,
    missing_fields: list[str],
) -> ScheduleAnalysisContext:
    return ScheduleAnalysisContext(
        original_text=previous_context.original_text if previous_context else text,
        latest_user_text=text,
        schedule=schedule,
        missing_fields=missing_fields,
        timezone=timezone,
        turn_count=(previous_context.turn_count + 1) if previous_context else 1,
    )

