from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field
from pydantic import ConfigDict, EmailStr


class MessageResponse(BaseModel):
    message: str = "Endpoint is not implemented yet."


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str
    email: EmailStr
    type: str
    exp: int
    iat: int


class ChildCreateRequest(BaseModel):
    name: str
    age: int = Field(ge=0, le=18)
    personality: str
    favorite_character: str
    favorite_toy: str = ""
    family_relationship: str = ""


class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    age: int
    personality: str
    favorite_character: str
    favorite_toy: str
    family_relationship: str
    created_at: datetime
    updated_at: datetime


class ChildUpdateRequest(BaseModel):
    name: str | None = None
    age: int | None = Field(None, ge=0, le=18)
    personality: str | None = None
    favorite_character: str | None = None
    favorite_toy: str | None = None
    family_relationship: str | None = None


class ExperienceCreateRequest(BaseModel):
    content: str
    experienced_at: date | None = None


class ExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    child_id: str
    content: str
    experienced_at: date
    created_at: datetime


class StoryGenerateRequest(BaseModel):
    child_id: str
    situation: str
    lesson: str
    mood: str
    category: str


class StoryGenerateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    body: str
    lesson: str
    image_url: str | None = None
    audio_url: str | None = None
    created_at: datetime


# ── 내부 서비스용 모델 ─────────────────────────────────────────────────���────


class Person(BaseModel):
    name: str
    relation: str
    kind: str = "기타"
    closeness: int = Field(default=3, ge=1, le=5)
    role_today: str = ""
    traits: list[str] = Field(default_factory=list)
    note: str = ""


class StoryRequest(BaseModel):
    diary_date: date
    diary: str
    people: list[Person] = Field(default_factory=list)


class Story(BaseModel):
    title: str
    body: str
