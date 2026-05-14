from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.schemas import MentoringDomain, TeamProfile


class MemberProfile(BaseModel):
    name: str = Field(default="", max_length=100)
    skills: list[str] = Field(default_factory=list, max_length=20)
    role: str = Field(default="", max_length=100)
    goals: str = Field(default="", max_length=1000)
    mentoring_needs: str = Field(default="", max_length=1000)
    project_experience: str = Field(default="", max_length=1000)
    personality: str = Field(default="", max_length=500)
    background: str = Field(default="", max_length=1000)


class TeamProfileRequest(BaseModel):
    members: list[MemberProfile] = Field(..., min_length=2, max_length=5)
    project_plan: str = Field(..., min_length=1, max_length=4000)
    fit_conditions: str = Field(default="", max_length=2000)


class TeamProfileResponse(BaseModel):
    team_profile: TeamProfile
    mentoring_domains: list[MentoringDomain] = Field(default_factory=list)
    member_count: int
    merged_skill_count: int
    llm_used: bool


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class TeamProfilePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    chat_messages: list[ChatMessage] = Field(default_factory=list, max_length=20)


class TeamProfilePromptResponse(BaseModel):
    team_profile: TeamProfile
    team_report: str
    chat_messages: list[ChatMessage]
    llm_used: bool
    draft_profile: TeamProfile
    missing_fields: list[str] = Field(default_factory=list)
    next_question: str | None = None
    ready_for_recommendation: bool
    status: Literal["collecting", "ready", "fallback"]


ProfileText4000 = Annotated[
    str, StringConstraints(min_length=1, max_length=4000, pattern=r"\S")
]
ProfilePhrase4000 = Annotated[
    str, StringConstraints(min_length=10, max_length=4000, pattern=r"\S")
]
ProfilePhrase2000 = Annotated[
    str, StringConstraints(min_length=10, max_length=2000, pattern=r"\S")
]
ProfileSkillText = Annotated[
    str, StringConstraints(min_length=2, max_length=1000, pattern=r"\S")
]
ProfileGoalText = Annotated[
    str, StringConstraints(min_length=2, max_length=4000, pattern=r"\S")
]


class TeamProfileLLMProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    members_rnr: ProfilePhrase4000
    project_plan_tech_goals: ProfilePhrase4000
    mentoring_needs: ProfilePhrase4000
    fit_conditions: ProfilePhrase2000
    maestro_program_goals: ProfileGoalText = Field(
        description="SW마에스트로 과정 목표를 인증, 취업, 창업, 기술 성장, 프로젝트 완성, 수료처럼 완성된 목표명으로 작성. 인, 취, 창 같은 한 글자 축약 금지. 여러 개면 쉼표로 구분."
    )
    skills: ProfileSkillText

    def to_team_profile(self) -> TeamProfile:
        return TeamProfile(**self.model_dump())


class TeamProfileSourceNotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    members_rnr: ProfilePhrase4000
    project_plan_tech_goals: ProfilePhrase4000
    mentoring_needs: ProfilePhrase4000
    fit_conditions: ProfilePhrase4000
    maestro_program_goals: ProfilePhrase4000
    skills: ProfilePhrase4000
    team_report: ProfilePhrase4000


class TeamProfilePromptLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_profile: TeamProfileLLMProfile
    team_report: ProfilePhrase4000
    source_notes: TeamProfileSourceNotes


class NextQuestionLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_question: ProfileText4000


class TeamProfileSynthesisLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    members_r_and_r: ProfilePhrase4000
    program_goals: ProfileGoalText = Field(
        description="SW마에스트로 과정 공통 목표를 인증, 취업, 창업, 기술 성장, 프로젝트 완성, 수료처럼 완성된 목표명으로 작성. 인, 취, 창 같은 한 글자 축약 금지. 여러 개면 쉼표로 구분."
    )
    mentoring_needs: ProfilePhrase4000
    mentoring_domains: list[MentoringDomain] = Field(..., min_length=1, max_length=3)
