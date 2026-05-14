"""Shared LangGraph state shape + event helpers.

Keys are camelCase strings so the pipeline output can be serialized to JSON
without further transformation — the frontend (``src/types/index.ts``) expects
camelCase DTOs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class UserInput(TypedDict):
    birthDate: str
    birthHour: str
    departure: str
    travelRange: str
    travelDuration: str
    preferredStyles: List[str]


class AgentState(TypedDict, total=False):
    # Inputs
    apiKey: str
    model: Optional[str]
    userInput: UserInput
    # Step outputs
    saju: Dict[str, Any]
    mapping: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    filterStats: Dict[str, Any]
    ranked: List[Dict[str, Any]]
    result: Dict[str, Any]


AGENT_ORDER: List[str] = [
    "input-validation",
    "saju-analysis",
    "travel-style-mapping",
    "destination-retrieval",
    "ranking",
    "response-generation",
]


def make_event(
    event_type: str,
    *,
    agent: Optional[str] = None,
    index: Optional[int] = None,
    total: Optional[int] = None,
    payload: Any = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an ``AgentEvent``-shaped dict compatible with the frontend."""
    out: Dict[str, Any] = {"type": event_type}
    if agent is not None:
        out["agent"] = agent
    if index is not None:
        out["index"] = index
    if total is not None:
        out["total"] = total
    if payload is not None:
        out["payload"] = payload
    if message is not None:
        out["message"] = message
    return out
