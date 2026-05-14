"""공통 데이터 모델. 변경은 [interface-change] PR + 5명 react 후에만."""
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    id: int | None = None
    start_at: datetime
    end_at: datetime
    title: str
    is_busy: bool = True


class HealthSnapshot(BaseModel):
    id: int | None = None
    date: date
    sleep_hours: float
    activity_minutes: int
    resting_hr: int | None = None


class WorkoutRecord(BaseModel):
    id: int | None = None
    date: date
    type: str
    duration_min: int
    muscles: list[str]
    intensity: int = Field(ge=1, le=5)


class WorkoutSlot(BaseModel):
    start: datetime
    end: datetime
    type: str
    target_muscles: list[str]
    intensity: int = Field(ge=1, le=5)
    rationale: str


class MuscleFatigueState(BaseModel):
    date: date
    fatigue: dict[str, int]  # 부위명 → 0~5


class ScheduleProposal(BaseModel):
    slots: list[WorkoutSlot]
    fatigue_timeline: list[MuscleFatigueState]


class AgentResponse(BaseModel):
    message: str
    proposal: ScheduleProposal | None = None
    needs_approval: bool = False


# ---------- API 요청/응답 모델 (FastAPI 게이트웨이 ↔ Flutter Web) ----------

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatChunk(BaseModel):
    """SSE 스트림 청크. type별 payload 스키마는 schemas/CLAUDE.md 참고."""

    type: Literal["text", "tool_call", "proposal", "done", "error"]
    payload: dict[str, Any]

