"""LangGraph @tool 래퍼. 순수 함수(tools/data_tools.py)와 LLM 인터페이스를 분리."""
from datetime import date

from langchain_core.tools import tool

from tools.data_tools import get_calendar as _get_calendar
from tools.data_tools import get_health as _get_health
from tools.data_tools import get_workouts as _get_workouts


@tool
def calendar_tool(start: str, end: str) -> list[dict]:
    """이번 주 사용자 캘린더 일정을 조회한다. start/end는 YYYY-MM-DD 형식."""
    try:
        events = _get_calendar(date.fromisoformat(start), date.fromisoformat(end))
        return [e.model_dump(mode="json") for e in events]
    except Exception:
        # D/E 미구현 또는 Supabase 미연결 시 빈 리스트로 파이프라인 유지
        return []


@tool
def health_tool(start: str, end: str) -> list[dict]:
    """최근 수면 시간·활동량·안정 심박수를 조회한다. start/end는 YYYY-MM-DD 형식."""
    try:
        snapshots = _get_health(date.fromisoformat(start), date.fromisoformat(end))
        return [s.model_dump(mode="json") for s in snapshots]
    except Exception:
        return []


@tool
def workouts_tool(start: str, end: str) -> list[dict]:
    """최근 운동 기록과 부위별 피로도를 조회한다. start/end는 YYYY-MM-DD 형식."""
    try:
        records = _get_workouts(date.fromisoformat(start), date.fromisoformat(end))
        return [r.model_dump(mode="json") for r in records]
    except Exception:
        return []
