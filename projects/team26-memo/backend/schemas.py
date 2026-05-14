"""Pydantic 요청/응답 스키마.

프론트엔드와의 API 계약을 강제한다.
요청: {agenda: str, transcript: str}
응답: {summary, missed_agenda, next_agenda, action_items: [{title,who,when,what,sub_items}]}
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


MAX_AGENDA_LEN = 10_000
MAX_TRANSCRIPT_LEN = 200_000


class AnalyzeRequest(BaseModel):
    agenda: str = Field(..., description="회의 안건 (자유 텍스트)")
    transcript: str = Field(..., description="회의 녹취록/회의록 본문")

    @field_validator("agenda")
    @classmethod
    def _agenda_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("agenda 가 비어 있습니다.")
        if len(v) > MAX_AGENDA_LEN:
            raise ValueError(f"agenda 가 너무 깁니다. ({len(v)} > {MAX_AGENDA_LEN})")
        return v

    @field_validator("transcript")
    @classmethod
    def _transcript_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("transcript 가 비어 있습니다.")
        if len(v) > MAX_TRANSCRIPT_LEN:
            raise ValueError(
                f"transcript 가 너무 깁니다. ({len(v)} > {MAX_TRANSCRIPT_LEN})"
            )
        return v


class SubActionItem(BaseModel):
    who: str = Field(default="", description="담당자")
    when: str = Field(default="", description="마감일 (YYYY-MM-DD 권장)")
    what: str = Field(default="", description="할 일")


class ActionItem(BaseModel):
    title: str = Field(default="", description="상위 티켓 제목")
    who: str = Field(default="", description="담당자")
    when: str = Field(default="", description="마감일 (YYYY-MM-DD 권장)")
    what: str = Field(default="", description="상위 티켓 설명/할 일")
    sub_items: List[SubActionItem] = Field(default_factory=list, description="하위 티켓 목록")


class AnalyzeResponse(BaseModel):
    summary: str = ""
    missed_agenda: str = ""
    next_agenda: str = ""
    action_items: List[ActionItem] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    provider: str
    version: str
