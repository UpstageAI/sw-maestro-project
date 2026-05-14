"""Pydantic models that flow through the LangGraph state and the API surface.

The frontend `lib/api.ts` mirrors these shapes — keep them in sync.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field

Severity = Literal["minor", "moderate", "critical"]
Level = Literal["basic", "intermediate", "advanced"]
FeedbackAction = Literal["regenerate", "refine_easier", "refine_harder", "accept"]


class UserFeedback(BaseModel):
    action: FeedbackAction = Field(
        description=(
            "regenerate = 같은 분야로 다른 follow-up 다시. "
            "refine_easier = 더 쉽게. "
            "refine_harder = 더 어렵게. "
            "accept = 만족, 다음 단계로."
        )
    )
    reason: str = Field(default="", description="사용자 자유 코멘트(선택)")
    target_index: int | None = Field(
        default=None,
        description="follow-ups 중 특정 index에 대한 피드백 (None이면 전체)",
    )
    session_id: str | None = Field(
        default=None,
        validation_alias="sessionId",
        serialization_alias="sessionId",
        description="피드백 후 갱신할 세션 식별자 (idempotent record_answer 대상).",
    )
    turn_id: str | None = Field(
        default=None,
        validation_alias="turnId",
        serialization_alias="turnId",
        description="피드백 후 갱신할 turn 식별자.",
    )

    model_config = {"populate_by_name": True}


# ---------- RAG / knowledge retrieval models ----------

class Chunk(BaseModel):
    """A retrieved document chunk from Chroma or web search."""
    text: str
    source: Literal["public", "user", "web"]
    file_name: str
    heading: str = ""
    score: float = 0.0
    url: str = ""  # web 청크인 경우 원본 URL. Chroma 청크는 빈 문자열.


class Citation(BaseModel):
    """Source citation attached to a follow-up question."""
    file_name: str
    heading: str = ""
    excerpt: str  # 3~6줄 길이로 축약된 청크 텍스트
    url: str = ""  # web 검색 결과인 경우 채워짐. 자료 기반은 빈 문자열.


# ---------- LLM-facing structured outputs ----------

class AnalysisNote(BaseModel):
    label: str = Field(description="짧은 요약 (한 줄, 명사형)")
    detail: str = Field(default="", description="한 문장 보충 설명")
    severity: Severity = Field(description="minor/moderate/critical")


AnswerQuality = Literal["good", "uncertain", "incorrect"]


class AnalysisOutput(BaseModel):
    notes: list[AnalysisNote] = Field(default_factory=list, max_length=6)
    answer_quality: AnswerQuality = Field(
        default="good",
        description=(
            "답변의 전반적 품질 등급. "
            "'good' = 답변이 합리적이며 깊이만 부족할 수 있음. "
            "'uncertain' = 사용자가 명시적으로 잘 모르겠다고 표현 (예: '잘 모르겠습니다', '처음 들어봅니다'). "
            "'incorrect' = 답변에 명백한 사실 오류가 있음 (개념 혼동·반대로 설명 등)."
        ),
    )
    explanation: str = Field(
        default="",
        description=(
            "answer_quality 가 uncertain 또는 incorrect 일 때만 채움. "
            "면접관이 친절하게 해설해주는 한국어 텍스트 (2~4문장). "
            "answer_quality 가 good 인 경우 빈 문자열."
        ),
    )
    question_intent: str = Field(
        default="",
        description=(
            "이 질문이 면접관 입장에서 무엇을 평가하려는지를 신입 지원자에게 "
            "설명하는 한국어 텍스트 (2~4문장). 평가 포인트 2~3개 명시. "
            "answer_quality 와 무관하게 항상 작성 — 학습 피드백 목적."
        ),
    )


class TermOutput(BaseModel):
    terms: list[str] = Field(
        default_factory=list,
        description="답변에 등장한 핵심 기술 용어 (영문 그대로 보존)",
        max_length=10,
    )


class FollowUpQuestion(BaseModel):
    level: Level
    text: str
    rationale: str = Field(default="")
    domain_label: str = Field(
        default="",
        description="이 질문이 다루는 분야 (예: '운영체제', '네트워크', 'Kubernetes'). "
        "프론트엔드의 도메인 로테이션 로직이 같은 분야 누적을 감지하는 데 사용합니다.",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="이 질문 생성에 활용한 검색 컨텍스트 출처 목록.",
    )


class FollowUpOutput(BaseModel):
    follow_ups: list[FollowUpQuestion] = Field(default_factory=list, max_length=5)


class EvaluationOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="0.0 - 1.0 종합 품질 점수")
    pass_threshold: bool = Field(description="재생성 없이 사용자에게 노출 가능 여부")
    reason: str = Field(default="")


# ---------- API surface ----------

class SubmitRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=2000)
    domains: list[str] = Field(
        default_factory=list,
        description="사용자가 온보딩에서 선택한 면접 분야 라벨들 (예: '운영체제', 'Spring').",
        max_length=10,
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="사용자가 직접 추가한 자유 키워드 (예: 'Kubernetes', 'gRPC').",
        max_length=10,
    )
    material_ids: list[str] = Field(
        default_factory=list,
        description="사용자가 등록한 자료 컬렉션 ID들. 비어있으면 public 컬렉션만 검색.",
        max_length=20,
    )
    session_id: str | None = Field(
        default=None,
        validation_alias="sessionId",
        serialization_alias="sessionId",
        description="채팅 세션 식별자. 없으면 BE가 신규 세션을 발급한다 (하위 호환).",
    )
    turn_id: str | None = Field(
        default=None,
        validation_alias="turnId",
        serialization_alias="turnId",
        description="이 답변이 채울 turn id. 없으면 BE가 신규 turn을 append한다 (하위 호환).",
    )

    model_config = {"populate_by_name": True}


# ---------- Materials (RAG ingest) ----------

MaterialKind = Literal["md", "pdf", "github"]
MaterialStatus = Literal["indexing", "ready", "failed"]


class MaterialResponse(BaseModel):
    id: str
    name: str
    kind: MaterialKind
    status: MaterialStatus
    chunks: int = 0
    error: str = ""


class GithubIngestRequest(BaseModel):
    repo_url: str = Field(min_length=1, max_length=500)


# ---------- Seed question generation ----------

class SeedQuestion(BaseModel):
    """Solar-generated structured output for the first interview question."""
    question: str = Field(description="면접관이 던지는 첫 질문 한 문장 (존댓말, 한국어)")
    domain_label: str = Field(
        description="질문이 속한 분야 또는 사용된 키워드 (예: '운영체제', 'Kubernetes')",
    )


class SeedRequest(BaseModel):
    track: Literal["cs", "stack"] = Field(
        description="cs = CS 기초, stack = 기술 스택",
    )
    domains: list[str] = Field(default_factory=list, max_length=10)
    keywords: list[str] = Field(default_factory=list, max_length=10)
    exclude_questions: list[str] = Field(
        default_factory=list,
        description="이미 세션 중에 던진 질문 텍스트들. 새 seed 가 이 중 하나와 동일하거나 매우 유사하면 안 됨.",
        max_length=20,
    )
    material_ids: list[str] = Field(
        default_factory=list,
        description=(
            "사용자가 등록한 자료 컬렉션 ID들. 비어있지 않으면 seed 가 해당 자료에서 "
            "토픽을 찾아 만들어지고 citations 가 채워짐."
        ),
        max_length=20,
    )
    session_id: str | None = Field(
        default=None,
        validation_alias="sessionId",
        serialization_alias="sessionId",
        description=(
            "있으면 기존 채팅 세션에 새 seed turn을 append, 없으면 BE가 신규 세션을 만들고 "
            "응답에 sessionId/turnId를 반환한다."
        ),
    )

    model_config = {"populate_by_name": True}


class SeedResponse(BaseModel):
    question: str
    domain_label: str
    citations: list[Citation] = Field(
        default_factory=list,
        description="자료 기반 seed 인 경우 채워짐. 정적 풀에서 만든 seed 는 빈 list.",
    )
    session_id: str = Field(default="", serialization_alias="sessionId")
    turn_id: str = Field(default="", serialization_alias="turnId")

    model_config = {"populate_by_name": True}


class SessionResult(BaseModel):
    question: str
    answer: str
    notes: list[AnalysisNote]
    follow_ups: list[FollowUpQuestion] = Field(serialization_alias="followUps")
    answer_quality: AnswerQuality = Field(
        default="good", serialization_alias="answerQuality",
    )
    explanation: str = ""
    question_intent: str = Field(
        default="", serialization_alias="questionIntent",
        description="면접관이 이 질문으로 평가하려는 의도. 답변 품질과 무관하게 항상 채워짐.",
    )
    evaluation: EvaluationOutput | None = None
    retrieved_context: list[Chunk] = Field(
        default_factory=list,
        serialization_alias="retrievedContext",
        description="FE 디버그/표시용 — 이번 세션에서 검색된 청크 목록.",
    )
    thread_id: str = Field(default="", serialization_alias="threadId")
    status: Literal["awaiting_feedback", "final"] = Field(default="final")
    session_id: str = Field(default="", serialization_alias="sessionId")
    next_turn_id: str | None = Field(default=None, serialization_alias="nextTurnId")

    model_config = {"populate_by_name": True}


# ---------- LangGraph state ----------

class GraphState(TypedDict, total=False):
    question: str
    answer: str
    domains: list[str]
    keywords: list[str]
    material_ids: list[str]
    analysis: AnalysisOutput
    terms: TermOutput
    retrieved_context: list[Chunk]
    follow_ups: FollowUpOutput
    evaluation: EvaluationOutput
    iteration_count: int
    feedback_count: int
    feedback: UserFeedback | None
    thread_id: str
