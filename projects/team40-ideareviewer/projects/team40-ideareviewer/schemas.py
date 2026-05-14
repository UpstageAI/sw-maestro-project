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


class PersonaSelectionReason(BaseModel):
    """LLM이 두 명의 페르소나를 고른 근거."""

    selected_card_ids: list[str] = Field(
        description=(
            "후보 풀에 실재하는 card_id 정확히 2개. "
            "card_id 외 다른 식별자(이름·직업 등)는 적지 말 것. "
            "코드 측 fallback이 결과 기준으로 다시 채울 수 있음."
        ),
    )
    per_persona_reasons: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "선택한 두 card_id 각각을 키로, 그 사람을 고른 이유 한 줄을 값으로. "
            "후보 목록의 사실(연령대·직업·지역·생활맥락·요약·목표·불편함)만 근거로 삼을 것. "
            "빈 dict로 두지 말 것 — 두 card_id 모두 반드시 채울 것."
        ),
    )
    pair_reason: str = Field(
        description=(
            "두 사람을 페어로 묶은 이유. "
            "공유 연결고리와 서로 다른 검증 관점을 후보 목록의 사실에 근거해 서술할 것. "
            "카드 이름·card_id·Anchor/Complement 같은 내부 역할명은 쓰지 말고, "
            "직업·생활맥락·연령대는 후보 목록의 표현만 사용할 것."
        ),
    )
    expected_review_angles: list[str] = Field(
        default_factory=list,
        description=(
            "이 페어가 검증할 핵심 리뷰 각도 3~5개. 빈 list로 두지 말 것. "
            "각 항목은 짧은 명사구 (예: '등록 난이도', '품질 신뢰')."
        ),
    )


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


class QualityFlag(BaseModel):
    """중간 산출물에 대한 deterministic 품질 판정."""

    code: str
    severity: Literal["info", "weak", "fail"]
    message: str
    point_id: str | None = None


class OpinionQualityReport(BaseModel):
    """한 페르소나 1차 의견에 대한 품질 메타데이터."""

    persona_id: str
    pass_point_ids: list[str] = Field(default_factory=list)
    weak_point_ids: list[str] = Field(default_factory=list)
    fail_point_ids: list[str] = Field(default_factory=list)
    flags: list[QualityFlag] = Field(default_factory=list)


class ReviewQualityReport(BaseModel):
    """한 교차 리뷰에 대한 품질 메타데이터."""

    reviewer_id: str
    target_id: str
    pass_feedback_ids: list[str] = Field(default_factory=list)
    weak_feedback_ids: list[str] = Field(default_factory=list)
    fail_feedback_ids: list[str] = Field(default_factory=list)
    flags: list[QualityFlag] = Field(default_factory=list)


__all__ = [
    "AgreementLevel",
    "DEFAULT_GUARDRAILS",
    "Opinion",
    "OpinionQualityReport",
    "PersonaSelectionReason",
    "PointFeedback",
    "QualityFlag",
    "RawNemotronPersona",
    "ReactionPoint",
    "Review",
    "ReviewQualityReport",
    "ServicePlanInput",
    "TargetUserPersonaCard",
]
