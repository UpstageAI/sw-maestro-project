"""Evaluator / reflection node."""

from __future__ import annotations

from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_HOLD, LIFECYCLE_READY_FOR_BE, PASS_ACTION, HOLD_DATA_INSUFFICIENT
from autocoin_ai.models import AgentState, append_check, ensure_state_shape, set_trace


def evaluator_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    lifecycle = next_state.get("lifecycle_status")
    if lifecycle == LIFECYCLE_FAILED:
        return next_state
    if lifecycle != LIFECYCLE_READY_FOR_BE:
        append_check(next_state, "evaluator_terminal_state_respected", "evaluator", "pass", ["lifecycle_status"])
        set_trace(next_state, "evaluator", ["NO_PROPOSAL_TO_PROMOTE"], ["lifecycle_status"], lifecycle or LIFECYCLE_HOLD)
        return next_state

    checks = next_state.get("verification_checks", [])
    has_policy = any(check["stage"] == "policy" and check["result"] == "pass" for check in checks)
    has_risk = any(check["stage"] == "risk" and check["result"] == "pass" for check in checks)
    if not (has_policy and has_risk):
        append_check(next_state, "evidence_sufficiency", "evaluator", "fail", ["verification_checks"])
        set_trace(next_state, "evaluator", ["EVIDENCE_INSUFFICIENT"], ["verification_checks"], LIFECYCLE_HOLD)
        next_state["lifecycle_status"] = LIFECYCLE_HOLD
        next_state["hold_reason"] = HOLD_DATA_INSUFFICIENT
        return next_state

    append_check(next_state, "evidence_sufficiency", "evaluator", "pass", ["verification_checks"])
    set_trace(next_state, "evaluator", ["EVIDENCE_SUFFICIENT"], ["verification_checks[-1]"], PASS_ACTION)
    next_state["lifecycle_status"] = LIFECYCLE_READY_FOR_BE
    return next_state
