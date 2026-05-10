"""Market / risk gate node."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from autocoin_ai.constants import (
    HOLD_DATA_INSUFFICIENT,
    HOLD_REVIEW_REQUIRED,
    LIFECYCLE_FAILED,
    LIFECYCLE_HOLD,
    LIFECYCLE_NO_ORDER,
    LIFECYCLE_READY_FOR_BE,
    PASS_ACTION,
)
from autocoin_ai.models import AgentState, append_check, effective_user_input, ensure_state_shape, set_trace


def _amount(intent):
    raw = intent.get("quoteOrderQty") or intent.get("quantity") or "0"
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return Decimal("0")


def risk_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    if next_state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return next_state

    intent = next_state.get("normalized_order_intent", {})
    user_input = effective_user_input(next_state)
    policy_refs = next_state.get("policy_context", {}).get("policy_refs", [])

    if user_input.get("market_snapshot_fresh") is False:
        append_check(next_state, "market_snapshot_freshness", "risk", "fail", ["request_context.user_input.market_snapshot_fresh"])
        set_trace(next_state, "risk", ["STALE_MARKET_SNAPSHOT"], ["verification_checks[-1]"], LIFECYCLE_HOLD)
        next_state["risk_assessment"] = {"verdict": "HOLD", "fail_reason": "STALE_MARKET_SNAPSHOT", "tools_called": []}
        next_state["lifecycle_status"] = LIFECYCLE_HOLD
        next_state["hold_reason"] = HOLD_DATA_INSUFFICIENT
        return next_state

    if user_input.get("requires_review") is True:
        append_check(next_state, "human_review_boundary", "risk", "fail", ["request_context.user_input.requires_review"])
        set_trace(next_state, "risk", ["HUMAN_REVIEW_REQUIRED"], ["verification_checks[-1]"], LIFECYCLE_HOLD)
        next_state["risk_assessment"] = {"verdict": "HOLD", "fail_reason": "HUMAN_REVIEW_REQUIRED", "tools_called": []}
        next_state["lifecycle_status"] = LIFECYCLE_HOLD
        next_state["hold_reason"] = HOLD_REVIEW_REQUIRED
        return next_state

    if intent.get("symbol") not in ("BTCUSDT", "ETHUSDT") or "policy.symbol_allowlist" not in policy_refs:
        append_check(next_state, "policy_symbol_allowed", "risk", "fail", ["policy_context.policy_refs"])
        set_trace(next_state, "risk", ["SYMBOL_NOT_ALLOWED"], ["verification_checks[-1]"], LIFECYCLE_NO_ORDER)
        next_state["risk_assessment"] = {"verdict": "NO_ORDER", "fail_reason": "SYMBOL_NOT_ALLOWED", "tools_called": []}
        next_state["lifecycle_status"] = LIFECYCLE_NO_ORDER
        next_state["hold_reason"] = None
        return next_state

    if _amount(intent) <= Decimal("0"):
        append_check(next_state, "order_amount_positive", "risk", "fail", ["normalized_order_intent"])
        set_trace(next_state, "risk", ["ORDER_AMOUNT_INVALID"], ["verification_checks[-1]"], LIFECYCLE_NO_ORDER)
        next_state["risk_assessment"] = {"verdict": "NO_ORDER", "fail_reason": "ORDER_AMOUNT_INVALID", "tools_called": []}
        next_state["lifecycle_status"] = LIFECYCLE_NO_ORDER
        next_state["hold_reason"] = None
        return next_state

    append_check(next_state, "risk_gate_rules", "risk", "pass", ["normalized_order_intent", "policy_context.policy_refs"])
    set_trace(next_state, "risk", ["ALL_CHECKS_PASSED"], ["verification_checks[-1]"], PASS_ACTION)
    next_state["risk_assessment"] = {"verdict": "ALLOW", "fail_reason": None, "tools_called": []}
    next_state["lifecycle_status"] = LIFECYCLE_READY_FOR_BE
    next_state["hold_reason"] = None
    return next_state
