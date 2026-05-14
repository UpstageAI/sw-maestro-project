"""Gateway API 계약 — packages/shared-types/src/gateway-api.ts와 매뉴얼 sync.

shared-types(TS)는 BFF의 type-safe fetch 클라이언트용. 본 파일은 Gateway 서버 측
요청 검증 + 응답 직렬화용 Pydantic v2 모델. 두 정의가 일치해야 하며, 한쪽만
변경 시 반드시 다른 쪽도 갱신할 것.

ADR 정합:
- ADR-0005 부록: state schema, structured outputs 7-enum mood
- ADR-0010: diary_text DB CHECK 50~1000, short_caption 1~100, honorific 1~20, keywords 1~1000, feedback 1~500
- ADR-0011: endpoint 시그니처
"""
from typing import Literal

from pydantic import BaseModel, Field

# ============================================================
# 도메인 (shared-types domain.ts 매뉴얼 sync)
# ============================================================

MoodTag = Literal["행복", "신남", "평온", "졸림", "심심", "슬픔", "까칠"]
Gender = Literal["male", "female", "unknown"]


class DiaryGenerationResult(BaseModel):
    """LLM 산출물. OpenAI structured outputs로 강제하는 schema."""

    diary_text: str = Field(min_length=50, max_length=1000)
    short_caption: str = Field(min_length=1, max_length=100)
    mood_tag: MoodTag


# ============================================================
# POST /diary/generate
# ============================================================


class GatewayGenerateRequest(BaseModel):
    session_id: str = Field(min_length=1)
    seq: Literal[1] = 1
    pet_id: str = Field(min_length=1)
    photo_signed_url: str = Field(min_length=1)
    keywords: str = Field(min_length=1, max_length=1000)
    honorific: str = Field(min_length=1, max_length=20)
    species: str = Field(min_length=1, max_length=20)
    gender: Gender
    recent_diaries: list[str] = Field(default_factory=list, max_length=3)


GatewayGenerateResponse = DiaryGenerationResult


# ============================================================
# POST /diary/regenerate
# ============================================================


class GatewayRegenerateRequest(BaseModel):
    session_id: str = Field(min_length=1)
    seq: int = Field(ge=2, le=4)
    pet_id: str = Field(min_length=1)
    photo_signed_url: str = Field(min_length=1)
    keywords: str = Field(min_length=1, max_length=1000)
    honorific: str = Field(min_length=1, max_length=20)
    species: str = Field(min_length=1, max_length=20)
    gender: Gender
    recent_diaries: list[str] = Field(default_factory=list, max_length=3)
    previous_diary_text: str = Field(min_length=1)
    feedback: str | None = Field(default=None, min_length=1, max_length=500)
    # 직전 generation의 vision 결과. 있으면 graph가 vision LLM 호출 skip.
    vision_description: str | None = Field(default=None, min_length=1, max_length=1000)


GatewayRegenerateResponse = DiaryGenerationResult


# ============================================================
# GET /health
# ============================================================


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
