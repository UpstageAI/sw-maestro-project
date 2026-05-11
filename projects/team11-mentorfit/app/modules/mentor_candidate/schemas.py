from __future__ import annotations

from typing import Annotated, List

from pydantic import BaseModel, Field

ShortText = Annotated[str, Field(min_length=1, max_length=200)]
CareerEntry = tuple[ShortText, int]


class TeamProfile(BaseModel):
    members_rnr: str = Field(..., min_length=1, max_length=4000)
    project_plan_tech_goals: str = Field(..., min_length=1, max_length=4000)
    mentoring_needs: str = Field(..., min_length=1, max_length=4000)
    fit_conditions: str = Field(default="", max_length=2000)
    maestro_program_goals: str = Field(..., min_length=1, max_length=4000)
    skills: str = Field(..., min_length=1, max_length=1000)


class Mentor(BaseModel):
    mentor_id: int
    name: str = Field(..., min_length=1, max_length=100)
    stacks: List[ShortText] = Field(default_factory=list, max_length=30)
    hobbie: str = Field(default="", max_length=1000)
    target: str = Field(default="", max_length=1000)
    is_overseas: bool
    is_new_mentor: bool
    can_plan: bool
    meeting_mode_preference: str = Field(default="", max_length=200)
    domains: List[ShortText] = Field(default_factory=list, max_length=20)
    is_certificated: bool
    career: List[CareerEntry] = Field(default_factory=list, max_length=20)


class CandidateResult(BaseModel):
    mentor_id: int
    rank: int = Field(..., ge=1, le=100)
    reason: str = Field(..., min_length=1, max_length=4000)
    weak_point: str = Field(..., min_length=1, max_length=4000)


class CandidateResultInternal(CandidateResult):
    extracted_facts: str = Field(..., min_length=1, max_length=4000)
    reasoning_process: str = Field(..., min_length=1, max_length=4000)
