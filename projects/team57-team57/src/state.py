from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReviewAgentState:
    store_id: int | None = None
    session_id: int | None = None
    raw_input_text: str = ""
    parsed_reviews: list[dict[str, Any]] = field(default_factory=list)
    store_context: dict[str, Any] = field(default_factory=dict)
    classified_reviews: list[dict[str, Any]] = field(default_factory=list)
    drafted_replies: list[dict[str, Any]] = field(default_factory=list)
    saved_review_ids: list[int] = field(default_factory=list)
    pattern_summary: dict[str, Any] = field(default_factory=dict)
    checklist: list[str] = field(default_factory=list)
    execution_log: list[str] = field(default_factory=list)
    backend_logs: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewAgentState":
        return cls(**data)
