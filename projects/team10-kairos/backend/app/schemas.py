from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ScheduleCandidate(BaseModel):
    title: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    location: Optional[str] = None
    reminder_minutes: Optional[int] = None
    schedule_type: Optional[str] = None


class ScheduleAnalysisContext(BaseModel):
    original_text: str
    latest_user_text: str
    schedule: ScheduleCandidate
    missing_fields: list[str] = Field(default_factory=list)
    timezone: str = "Asia/Seoul"
    turn_count: int = 1


class AnalyzeScheduleResponse(BaseModel):
    original_text: str
    schedule: ScheduleCandidate
    missing_fields: list[str] = Field(default_factory=list)
    needs_confirmation: bool = True
    analysis_context: ScheduleAnalysisContext
    message: str = "일정 정보를 확인해주세요."


class AnalyzeScheduleRequest(BaseModel):
    text: str = Field(..., min_length=1)
    timezone: str = "Asia/Seoul"
    analysis_context: Optional[ScheduleAnalysisContext] = None


class ScheduleCreate(BaseModel):
    title: str = Field(..., min_length=1)
    start_at: datetime
    end_at: Optional[datetime] = None
    location: Optional[str] = None
    reminder_minutes: int = Field(default=30, ge=0)
    schedule_type: Optional[str] = None
    original_text: Optional[str] = None
    session_id: Optional[str] = None  # Google Calendar 연동 세션


class ScheduleUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    location: Optional[str] = None
    reminder_minutes: Optional[int] = Field(default=None, ge=0)
    schedule_type: Optional[str] = None
    original_text: Optional[str] = None
    status: Optional[str] = None
    session_id: Optional[str] = None  # Google Calendar 연동 세션


class BusySlot(BaseModel):
    start: datetime
    end: datetime


class AvailabilityResponse(BaseModel):
    time_min: datetime
    time_max: datetime
    busy: list[BusySlot]


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    start_at: datetime
    end_at: Optional[datetime]
    location: Optional[str]
    reminder_minutes: int
    schedule_type: Optional[str]
    google_event_id: Optional[str]
    status: str
