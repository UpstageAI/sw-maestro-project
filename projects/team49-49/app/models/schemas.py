from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


CARD_TYPES = (
    "idea",
    "problem",
    "target_user",
    "hypothesis",
    "evidence",
    "decision",
    "risk",
    "feature",
    "question",
)
CARD_STATUSES = ("proposed", "needs_validation", "validated", "rejected", "decided", "needs_review")
CONFIDENCE_LEVELS = ("low", "medium", "high")
RELATION_TYPES = ("supports", "contradicts", "duplicates", "related_to", "derived_from")

CardType = Literal[
    "idea",
    "problem",
    "target_user",
    "hypothesis",
    "evidence",
    "decision",
    "risk",
    "feature",
    "question",
]
CardStatus = Literal["proposed", "needs_validation", "validated", "rejected", "decided", "needs_review"]
Confidence = Literal["low", "medium", "high"]
RelationType = Literal["supports", "contradicts", "duplicates", "related_to", "derived_from"]


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120, description="Workspace display name.")
    description: str = Field(default="", max_length=500, description="Short workspace description.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Demo Workspace",
                "description": "데모 시연용 최종 workspace",
            }
        }
    )


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120, description="New workspace display name.")
    description: str | None = Field(default=None, max_length=500, description="New workspace description.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Renamed Workspace",
                "description": "수정된 설명",
            }
        }
    )


class WorkspaceRead(BaseModel):
    id: int
    name: str
    description: str
    created_at: str


class RawDocumentRead(BaseModel):
    id: int
    workspace_id: int
    filename: str
    document_type: str
    source_type: str
    source_url: str
    external_id: str
    content: str
    created_at: str


class RawDocumentUpdate(BaseModel):
    filename: str | None = Field(default=None, min_length=1, max_length=240, description="Stored source filename.")
    source_type: str | None = Field(default=None, min_length=1, max_length=80, description="Source type such as manual, md, txt, notion, github, or web.")
    source_url: str | None = Field(default=None, max_length=1000, description="Original source URL.")
    external_id: str | None = Field(default=None, max_length=500, description="Provider-native id or reference.")
    content: str | None = Field(default=None, min_length=1, description="Source text/markdown. Updating this re-indexes chunks and cards.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "edited-source.md",
                "source_type": "manual",
                "source_url": "",
                "external_id": "manual-demo",
                "content": "결정: 수정된 원문에서 카드를 다시 추출한다.",
            }
        }
    )


class KnowledgeCardCreate(BaseModel):
    workspace_id: int
    source_document_id: int
    source_chunk_id: int
    card_type: CardType
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: CardStatus = "proposed"
    confidence: Confidence = "medium"


class KnowledgeCardCreateRequest(BaseModel):
    source_document_id: int | None = Field(
        default=None,
        ge=1,
        description="Existing raw document id. Omit with source_chunk_id to create a manual card source.",
    )
    source_chunk_id: int | None = Field(
        default=None,
        ge=1,
        description="Existing chunk id. Omit with source_document_id to create a manual card source.",
    )
    card_type: CardType = Field(description="Knowledge card type.")
    title: str = Field(min_length=1, max_length=200, description="Short card title.")
    summary: str = Field(min_length=1, description="Normalized card summary.")
    evidence_quote: str = Field(min_length=1, description="Grounding quote from the source.")
    keywords: list[str] = Field(default_factory=list, description="Search keywords.")
    tags: list[str] = Field(default_factory=list, description="User-editable card tags.")
    status: CardStatus = Field(default="proposed", description="Decision/review status.")
    confidence: Confidence = Field(default="medium", description="Confidence level.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "card_type": "decision",
                "title": "SQLite 우선",
                "summary": "MVP에서는 SQLite를 우선 사용한다.",
                "evidence_quote": "결정: MVP에서는 SQLite를 우선 사용한다.",
                "keywords": ["SQLite", "MVP"],
                "tags": ["decided"],
                "status": "decided",
                "confidence": "high",
            }
        }
    )


class KnowledgeCardUpdate(BaseModel):
    card_type: CardType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, min_length=1)
    evidence_quote: str | None = Field(default=None, min_length=1)
    keywords: list[str] | None = None
    tags: list[str] | None = None
    status: CardStatus | None = None
    confidence: Confidence | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "validated",
                "tags": ["reviewed", "demo"],
            }
        }
    )


class KnowledgeCardRead(BaseModel):
    id: int
    workspace_id: int
    source_document_id: int
    source_chunk_id: int
    card_type: CardType
    title: str
    summary: str
    evidence_quote: str
    keywords: list[str]
    tags: list[str]
    status: CardStatus
    confidence: Confidence
    created_at: str
    updated_at: str


class KnowledgeCardDetail(KnowledgeCardRead):
    source_document: dict[str, Any]
    source_chunk: dict[str, Any]
    relations: list[dict[str, Any]]


class QAResponse(BaseModel):
    answer: str
    confidence: Confidence
    evidence_cards: list[dict]
    evidence_chunks: list[dict]
    missing_evidence: list[str] = Field(default_factory=list)
