from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import settings
from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile
from app.modules.report.schemas import RecommendationReport
from app.modules.team_profile.schemas import ChatMessage


class RecommendationRequest(BaseModel):
    chat_messages: list[ChatMessage] = Field(default_factory=list, max_length=100)
    team_profile: TeamProfile | None = None
    draft_profile: TeamProfile | None = None
    team_report: str = Field(..., min_length=1, max_length=8000)
    ready_for_recommendation: bool
    collection_status: Literal["collecting", "ready", "fallback"]
    current_matching_status: str | None = Field(default=None, max_length=4000)
    top_k: int = Field(default=settings.candidate_top_k, ge=1, le=settings.recommendation_top_k_max)
    prefilter_top_n: int | None = Field(default=None, ge=10, le=100)


class RecommendationResponse(BaseModel):
    team_profile: TeamProfile
    team_report: str
    candidates: list[CandidateResult] = Field(default_factory=list, max_length=20)
    combinations: list[CombCandidateResult] = Field(default_factory=list, max_length=20)
    mentors: list[Mentor] = Field(default_factory=list, max_length=300)
    recommendation_report: RecommendationReport
