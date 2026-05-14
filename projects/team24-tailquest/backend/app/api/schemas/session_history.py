"""API response shapes for session history endpoints.

Mirror these in `frontend/lib/api.ts`. All fields use `serialization_alias`
camelCase + `populate_by_name=True` so internal Python code can construct
them with snake_case kwargs but JSON output is camelCase.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.graph.schema import (
    AnalysisNote,
    AnswerQuality,
    Chunk,
    Citation,
    FollowUpQuestion,
)


class SessionSummary(BaseModel):
    id: str
    track: str
    title: str
    user_id: str | None = Field(default=None, serialization_alias="userId")
    domains: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    material_ids: list[str] = Field(
        default_factory=list, serialization_alias="materialIds",
    )
    turn_count: int = Field(default=0, serialization_alias="turnCount")
    last_score: int | None = Field(default=None, serialization_alias="lastScore")
    created_at: float = Field(default=0.0, serialization_alias="createdAt")
    updated_at: float = Field(default=0.0, serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class TurnDetail(BaseModel):
    id: str
    seq: int
    level: str = ""
    source: str = ""
    domain_label: str = Field(default="", serialization_alias="domainLabel")
    question: str = ""
    rationale: str = ""
    answer: str | None = None

    notes: list[AnalysisNote] = Field(default_factory=list)
    follow_ups: list[FollowUpQuestion] = Field(
        default_factory=list, serialization_alias="followUps",
    )
    retrieved_context: list[Chunk] = Field(
        default_factory=list, serialization_alias="retrievedContext",
    )
    citations: list[Citation] = Field(default_factory=list)

    answer_quality: AnswerQuality | str = Field(
        default="", serialization_alias="answerQuality",
    )
    explanation: str = ""
    question_intent: str = Field(default="", serialization_alias="questionIntent")
    score: int | None = None
    thread_id: str | None = Field(default=None, serialization_alias="threadId")
    created_at: float = Field(default=0.0, serialization_alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class SessionDetail(BaseModel):
    id: str
    track: str
    title: str
    domains: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    material_ids: list[str] = Field(
        default_factory=list, serialization_alias="materialIds",
    )
    turn_count: int = Field(default=0, serialization_alias="turnCount")
    last_score: int | None = Field(default=None, serialization_alias="lastScore")
    created_at: float = Field(default=0.0, serialization_alias="createdAt")
    updated_at: float = Field(default=0.0, serialization_alias="updatedAt")
    turns: list[TurnDetail] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


def summary_from_row(row: dict[str, Any]) -> SessionSummary:
    return SessionSummary(
        id=row["id"],
        track=row["track"],
        title=row["title"],
        user_id=row.get("user_id"),
        domains=row.get("domains") or [],
        keywords=row.get("keywords") or [],
        material_ids=row.get("material_ids") or [],
        turn_count=row.get("turn_count", 0),
        last_score=row.get("last_score"),
        created_at=row.get("created_at", 0.0),
        updated_at=row.get("updated_at", 0.0),
    )


def detail_from_row(row: dict[str, Any]) -> SessionDetail:
    return SessionDetail(
        id=row["id"],
        track=row["track"],
        title=row["title"],
        domains=row.get("domains") or [],
        keywords=row.get("keywords") or [],
        material_ids=row.get("material_ids") or [],
        turn_count=row.get("turn_count", 0),
        last_score=row.get("last_score"),
        created_at=row.get("created_at", 0.0),
        updated_at=row.get("updated_at", 0.0),
        turns=[TurnDetail.model_validate(t) for t in row.get("turns", [])],
    )
