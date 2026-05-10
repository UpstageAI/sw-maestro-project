"""Execution / report interpretation node.

This node interprets BE-provided completion payloads only. It never submits,
signs, timestamps, or calls Binance.
"""

from __future__ import annotations

from autocoin_ai.constants import LIFECYCLE_BE_REJECTED, LIFECYCLE_FAILED, LIFECYCLE_REPORT_READY
from autocoin_ai.models import AgentState, append_check, ensure_state_shape, set_trace


def execution_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    payload = next_state.get("completion_payload", {})
    has_execution = "execution_result" in payload
    has_rejection = "be_rejection_evidence" in payload
    if has_execution == has_rejection:
        append_check(next_state, "completion_payload_contract", "execution", "fail", ["completion_payload"])
        set_trace(next_state, "execution", ["COMPLETION_PAYLOAD_INVALID"], ["completion_payload"], LIFECYCLE_FAILED)
        set_trace(next_state, "run_summary", ["RUN_FAILED"], ["decision_trace.execution"], LIFECYCLE_FAILED)
        next_state["lifecycle_status"] = LIFECYCLE_FAILED
        return next_state

    if has_rejection:
        next_state["be_rejection_evidence"] = payload["be_rejection_evidence"]
        append_check(next_state, "be_revalidation_result", "be_revalidation", "fail", ["be_rejection_evidence"])
        set_trace(next_state, "execution", ["BE_REVALIDATION_REJECTED"], ["be_rejection_evidence"], LIFECYCLE_BE_REJECTED)
        set_trace(next_state, "run_summary", ["BE_REJECTED_REPORTED"], ["decision_trace.execution"], LIFECYCLE_BE_REJECTED)
        next_state["lifecycle_status"] = LIFECYCLE_BE_REJECTED
        next_state["report"] = {"status": LIFECYCLE_BE_REJECTED, "message": "BE deterministic revalidation blocked the proposal."}
        return next_state

    next_state["execution_result"] = payload["execution_result"]
    append_check(next_state, "execution_result_contract", "execution", "pass", ["execution_result"])
    set_trace(next_state, "execution", ["ORDER_RESPONSE_VERIFIED"], ["execution_result.orderId"], LIFECYCLE_REPORT_READY)
    set_trace(next_state, "run_summary", ["FINAL_REPORT_READY"], ["decision_trace.execution"], LIFECYCLE_REPORT_READY)
    next_state["lifecycle_status"] = LIFECYCLE_REPORT_READY
    next_state["report"] = {"status": LIFECYCLE_REPORT_READY, "message": "Execution result interpreted for user reporting."}
    return next_state
