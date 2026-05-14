from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile


class ReportGenerationRequest(BaseModel):
    team_profile: TeamProfile
    team_report: str = Field(..., min_length=1, max_length=8000)
    candidates: list[CandidateResult] = Field(default_factory=list, max_length=20)
    combinations: list[CombCandidateResult] = Field(default_factory=list, max_length=10)
    mentors: list[Mentor] = Field(default_factory=list, min_length=1, max_length=50)
    current_matching_status: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_mentor_ids(self) -> "ReportGenerationRequest":
        mentor_ids = {mentor.mentor_id for mentor in self.mentors}
        candidate_ids = {candidate.mentor_id for candidate in self.candidates}
        required_ids = set(candidate_ids)
        for combination in self.combinations:
            required_ids.add(combination.mentor_id)
            required_ids.update(combination.candidate_ids)

        missing_ids = sorted(required_ids - mentor_ids)
        if missing_ids:
            raise ValueError(f"mentors 입력에 없는 멘토 ID가 포함되어 있습니다: {missing_ids}")
        return self


class ReportMentorSummary(BaseModel):
    mentor_id: int
    name: str
    role: Literal["main", "supplement"]
    reason: str
    weak_point: str


class ReportCombination(BaseModel):
    rank: int
    main_mentor: ReportMentorSummary
    supplement_mentors: list[ReportMentorSummary] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weak_points: list[str] = Field(default_factory=list)
    recommendation_reason: str


class RecommendationReport(BaseModel):
    team_summary: str
    confidence_basis: str
    candidate_summary: str
    combinations: list[ReportCombination] = Field(default_factory=list)
    final_recommendation: str
    cautions: list[str] = Field(default_factory=list)
    generated_at: str
