from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

Stage = Literal[
    "awaiting_jd",
    "criteria_review",
    "candidate_intake",
    "results",
]


class ChatState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    job_id: str | None
    locale: str
    stage: Stage
    pending_jd_title: str | None
    pending_candidate: dict[str, Any]
