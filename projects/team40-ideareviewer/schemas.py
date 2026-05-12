"""전원 공유 — Pydantic 스키마 정의. 임의 수정 금지."""

from typing import Literal

from pydantic import BaseModel, Field

AgreementLevel = Literal["agree", "disagree"]

DEFAULT_GUARDRAILS = [
    "전문가처럼 평가하지 말고 실제 사용자 입장에서 반응한다",
    "성별, 나이, 지역, 학력만으로 성향을 단정하지 않는다",
    "원본 페르소나에 없는 경험을 만들어내지 않는다",
    "서비스 기획에 없는 기능을 있다고 가정하지 않는다",
]


class RawNemotronPersona(BaseModel):
    """HuggingFace 원본 페르소나 데이터. 런타임에서는 직접 사용하지 않는다."""

    uuid: str

    persona: str | None = None
    professional_persona: str | None = None
    cultural_background: str | None = None
    sports_persona: str | None = None
    arts_persona: str | None = None
    travel_persona: str | None = None
    culinary_persona: str | None = None
    family_persona: str | None = None

    skills_and_expertise: str | None = None
    skills_and_expertise_list: list[str] = Field(default_factory=list)
    hobbies_and_interests: str | None = None
    hobbies_and_interests_list: list[str] = Field(default_factory=list)
    career_goals_and_ambitions: str | None = None

    sex: str | None = None
    age: int | None = None
    occupation: str | None = None
    province: str | None = None
    district: str | None = None
    education_level: str | None = None
    marital_status: str | None = None
    military_status: str | None = None
    housing_type: str | None = None
    family_type: str | None = None
    bachelors_field: str | None = None
    country: str | None = None


class TargetUserPersonaCard(BaseModel):
    """런타임 프롬프트에서 실제로 사용하는 페르소나 카드."""

    card_id: str
    source_uuid: str
    display_name: str

    age_group: str | None = None
    sex: str | None = None
    occupation: str | None = None
    region: str | None = None

    one_line_summary: str
    life_context: str

    user_goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    positive_triggers: list[str] = Field(default_factory=list)
    negative_triggers: list[str] = Field(default_factory=list)

    speaking_style: str
    guardrails: list[str] = Field(default_factory=lambda: DEFAULT_GUARDRAILS.copy())


class ServicePlanInput(BaseModel):
    """사용자 자유 입력을 구조화한 서비스 기획안."""

    raw_text: str
    title: str | None = None
    description: str | None = None
    target: str | None = None
    key_features: list[str] = Field(default_factory=list)
    concerns: str | None = None


class ReactionPoint(BaseModel):
    """페르소나 의견의 개별 반응 포인트."""

    point_id: str
    title: str
    detail: str


class Opinion(BaseModel):
    """각 페르소나의 1차 의견."""

    persona_id: str
    positive_points: list[ReactionPoint] = Field(default_factory=list)
    negative_points: list[ReactionPoint] = Field(default_factory=list)
    would_use: bool
    would_use_description: str | None = None


class PointFeedback(BaseModel):
    """상대 의견의 특정 point_id에 대한 교차 피드백."""

    target_point_id: str
    agreement: AgreementLevel
    comment: str


class Review(BaseModel):
    """상대 페르소나 의견을 읽은 뒤의 리뷰."""

    reviewer_id: str
    target_id: str
    point_feedbacks: list[PointFeedback] = Field(default_factory=list)
    overall_comment: str
    revised_would_use: bool


__all__ = [
    "AgreementLevel",
    "DEFAULT_GUARDRAILS",
    "RawNemotronPersona",
    "TargetUserPersonaCard",
    "ServicePlanInput",
    "ReactionPoint",
    "Opinion",
    "PointFeedback",
    "Review",
]
