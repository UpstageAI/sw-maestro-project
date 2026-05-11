from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

ShortText = Annotated[str, Field(min_length=1, max_length=1000)]


class CombCandidateResult(BaseModel):
    mentor_id: int
    candidate_ids: list[int] = Field(default_factory=list, max_length=5)
    strengths: list[ShortText] = Field(default_factory=list, max_length=5)
    weak_points: list[ShortText] = Field(default_factory=list, max_length=5)
    rank: int = Field(..., ge=1, le=100)
    reason: str = Field(..., min_length=1, max_length=4000)
    weak_point: str = Field(..., min_length=1, max_length=4000)


class CombinationResponse(BaseModel):
    combinations: list[CombCandidateResult] = Field(default_factory=list, max_length=10)
