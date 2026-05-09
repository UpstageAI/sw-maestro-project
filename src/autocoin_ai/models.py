"""Typed state helpers for the standalone AI Agent."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Optional, TypedDict, cast

from typing_extensions import NotRequired

from autocoin_ai.constants import CHECK_STAGES, TRACE_STAGES


JsonDict = Dict[str, Any]


class TraceEntry(TypedDict):
    reason_codes: List[str]
    evidence_refs: List[str]
    final_action: str
    notes: NotRequired[str]


class VerificationCheck(TypedDict):
    name: str
    stage: str
    result: str
    evidence_refs: List[str]


class DecisionTraceHistoryEntry(TypedDict):
    decision_trace: Dict[str, TraceEntry]
    verification_checks_count: int


class AgentState(TypedDict):
    run_id: str
    request_context: JsonDict
    policy_context: JsonDict
    normalized_order_intent: JsonDict
    lifecycle_status: str
    hold_reason: Optional[str]
    decision_trace: Dict[str, TraceEntry]
    verification_checks: List[VerificationCheck]
    completion_payload: JsonDict
    execution_result: JsonDict
    be_rejection_evidence: JsonDict
    report: JsonDict
    resume_history: List[JsonDict]
    decision_trace_history: List[DecisionTraceHistoryEntry]


def empty_trace_entry() -> TraceEntry:
    return {"reason_codes": [], "evidence_refs": [], "final_action": ""}


def canonical_trace() -> Dict[str, TraceEntry]:
    return {stage: empty_trace_entry() for stage in TRACE_STAGES}


def ensure_state_shape(state: Mapping[str, Any]) -> AgentState:
    next_state: Dict[str, Any] = dict(deepcopy(state))
    next_state.setdefault("policy_context", {"policy_refs": []})
    next_state.setdefault("normalized_order_intent", {})
    next_state.setdefault("lifecycle_status", "")
    next_state.setdefault("decision_trace", canonical_trace())
    for stage in TRACE_STAGES:
        next_state["decision_trace"].setdefault(stage, empty_trace_entry())
    next_state.setdefault("verification_checks", [])
    next_state.setdefault("hold_reason", None)
    next_state.setdefault("completion_payload", {})
    next_state.setdefault("execution_result", {})
    next_state.setdefault("be_rejection_evidence", {})
    next_state.setdefault("report", {})
    next_state.setdefault("resume_history", [])
    next_state.setdefault("decision_trace_history", [])
    return cast(AgentState, cast(object, next_state))


def append_check(state: AgentState, name: str, stage: str, result: str, evidence_refs: List[str]) -> None:
    if stage not in CHECK_STAGES:
        raise ValueError("invalid verification stage: %s" % stage)
    state.setdefault("verification_checks", []).append(
        {"name": name, "stage": stage, "result": result, "evidence_refs": evidence_refs}
    )


def set_trace(
    state: AgentState,
    stage: str,
    reason_codes: List[str],
    evidence_refs: List[str],
    final_action: str,
    notes: Optional[str] = None,
) -> None:
    if stage not in TRACE_STAGES:
        raise ValueError("invalid trace stage: %s" % stage)
    entry: TraceEntry = {
        "reason_codes": reason_codes,
        "evidence_refs": evidence_refs,
        "final_action": final_action,
    }
    if notes:
        entry["notes"] = notes
    state.setdefault("decision_trace", canonical_trace())[stage] = entry


def state_copy(state: Mapping[str, Any]) -> AgentState:
    return cast(AgentState, cast(object, deepcopy(state)))
