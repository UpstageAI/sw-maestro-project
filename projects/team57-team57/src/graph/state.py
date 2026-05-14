"""Graph state schema — single source of truth for what flows between nodes."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict
from operator import add


NodeKind = Literal[
    "memory_read",
    "memory_write",
    "transform",
    "llm",
    "router",
    "sql_read",
    "sql_write",
]


class NodeLogEntry(TypedDict, total=False):
    """노드 1회 실행에 대한 백엔드 트레이스 항목.

    UI(`render_node_trace`)가 이걸 표 형태로 표시하고, LLM 종류는 prompt/response
    preview 를 함께 노출.
    """

    node: str
    started_at: str       # ISO timestamp
    duration_ms: int
    kind: NodeKind
    summary: str          # 한 줄 요약
    details: dict[str, Any]   # 종류별 페이로드 (model/prompt_preview/sql/...)


class ReviewState(TypedDict, total=False):
    """1 review = 1 graph invocation. Fields are filled progressively by nodes."""

    # 입력 (graph.invoke 시점)
    place_id: str
    review_id: str
    raw_text: str
    review_created_at: str  # ISO timestamp

    # load_context 출력
    place_metadata: dict
    tone_samples: list[dict]
    feedback_hints: list[str]

    # pii_mask 출력
    masked_text: str
    # P0-3: 한국어 비율이 임계 미만이면 LLM 호출 건너뜀 → noop_drafter 분기
    lang_skip: bool
    lang_skip_reason: str

    # classifier 출력
    sentiment: Literal["positive", "negative", "neutral"]
    categories: list[dict]   # [{"category": "맛", "confidence": 0.8}, ...]
    confidence: float
    risk_flag: bool
    risk_reason: str | None
    # P0-2: classifier가 2회 재시도 후에도 실패하면 True. 다운스트림은 안전 기본값으로 통과.
    classification_failed: bool
    classification_error: str

    # drafter 출력
    reply_draft: str
    drafter_used: str   # "thanks" | "apology" | "apology_lowconf" | "neutral" | "noop"
    # P0-5: drafter 후처리에서 치환된 위험 표현 기록 (사용자 가시 trace)
    safety_notes: list[str]

    # memory_save 출력
    reply_id: str

    # 백엔드 트레이스 — 각 노드가 append (Annotated[..., add] 로 누적)
    node_log: Annotated[list[NodeLogEntry], add]
