from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Criterion(BaseModel):
    name: str
    description: str
    weight: int = Field(ge=0, le=100)


class Evidence(BaseModel):
    source_type: Literal["resume", "github", "blog", "manual", "system"] = "system"
    source_ref: str
    snippet: str
    confidence: int = Field(ge=0, le=100, default=50)


class JobCreate(BaseModel):
    title: str
    jd_text: str


class JobRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    jd_text: str
    criteria: list[Criterion] = Field(default_factory=list)
    status: Literal["draft", "criteria_confirmed", "evaluating", "completed"] = "draft"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CandidateCreate(BaseModel):
    name: str
    resume_text: str
    github_url: str | None = None
    portfolio_url: str | None = None
    source_filename: str | None = None


class ResumeProject(BaseModel):
    name: str
    bullets: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class ResumeExperience(BaseModel):
    title: str
    bullets: list[str] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    title: str
    details: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    headline: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    section_hints: list[str] = Field(default_factory=list)
    section_summaries: dict[str, list[str]] = Field(default_factory=dict)
    projects: list[str] = Field(default_factory=list)
    experience_items: list[str] = Field(default_factory=list)
    education_items: list[str] = Field(default_factory=list)
    structured_projects: list[ResumeProject] = Field(default_factory=list)
    structured_experience: list[ResumeExperience] = Field(default_factory=list)
    structured_education: list[ResumeEducation] = Field(default_factory=list)


class GitHubRepoSummary(BaseModel):
    name: str
    html_url: str
    description: str | None = None
    language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    topics: list[str] = Field(default_factory=list)
    homepage: str | None = None
    readme_excerpt: str | None = None
    language_bytes: dict[str, int] = Field(default_factory=dict)
    recent_commit_headlines: list[str] = Field(default_factory=list)
    recent_commit_timestamps: list[str] = Field(default_factory=list)
    root_entries: list[str] = Field(default_factory=list)
    sample_code_paths: list[str] = Field(default_factory=list)
    sample_code_signals: list[str] = Field(default_factory=list)
    detected_frameworks: list[str] = Field(default_factory=list)
    has_tests: bool = False
    has_ci: bool = False
    has_dockerfile: bool = False
    updated_at: str | None = None


class GitHubProfileSnapshot(BaseModel):
    username: str
    profile_url: str
    display_name: str | None = None
    bio: str | None = None
    company: str | None = None
    blog: str | None = None
    location: str | None = None
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    top_languages: list[str] = Field(default_factory=list)
    recent_repos: list[GitHubRepoSummary] = Field(default_factory=list)
    recent_commit_count: int = 0
    last_activity_at: str | None = None
    fetched_at: datetime = Field(default_factory=utc_now)


class CandidateRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    name: str
    resume_text: str
    masked_resume_text: str
    github_url: str | None = None
    portfolio_url: str | None = None
    source_filename: str | None = None
    extracted_urls: list[str] = Field(default_factory=list)
    parsed_profile: CandidateProfile = Field(default_factory=CandidateProfile)
    github_status: Literal["not_requested", "fetched", "failed", "skipped"] = "not_requested"
    github_failure_reason: str | None = None
    github_profile: GitHubProfileSnapshot | None = None
    created_at: datetime = Field(default_factory=utc_now)


class MaskedToken(BaseModel):
    token: str
    original: str
    kind: Literal["name", "email", "phone", "rrn"]


class MaskingResult(BaseModel):
    masked_text: str
    tokens: list[MaskedToken] = Field(default_factory=list)
    safe_for_llm: bool = True
    failure_reasons: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    candidate_id: str
    jd_score: int = Field(ge=0, le=100)
    alignment_score: int = Field(ge=0, le=100)
    summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class AuditLogRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str | None = None
    event_type: str
    entity_id: str
    payload: dict
    created_at: datetime = Field(default_factory=utc_now)


class TokenMappingRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    candidate_id: str
    token: str
    original: str
    kind: Literal["name", "email", "phone", "rrn"]
    created_at: datetime = Field(default_factory=utc_now)
