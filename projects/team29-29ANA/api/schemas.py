"""FastAPI 요청/응답 스키마."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JobAcceptedResponse(BaseModel):
    job_id: str
    session_id: str | None = None
    status_url: str
    message: str


class AnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, description="사용자의 면접 답변")
    question_id: str | None = Field(None, description="프론트가 보고 있는 현재 질문 id")


class ReportRequest(BaseModel):
    force: bool = Field(
        False,
        description="True이면 최소 묶음 수 조건을 만족하지 않아도 현재 history 기준으로 리포트를 생성",
    )


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    session_id: str | None
    status: str
    step: str
    progress: int
    message: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str
    updated_at: str
