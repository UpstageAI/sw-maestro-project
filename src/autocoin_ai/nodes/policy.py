"""Policy / planning node."""

from __future__ import annotations

from autocoin_ai.constants import LIFECYCLE_FAILED, PASS_ACTION
from autocoin_ai.models import AgentState, append_check, effective_user_input, ensure_state_shape, set_trace
from autocoin_ai.validators import validate_request_context


def policy_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    request_context = next_state.get("request_context", {})
    missing = validate_request_context(request_context)
    if missing:
        append_check(next_state, "initial_request_contract", "policy", "fail", ["request_context"])
        set_trace(
            next_state,
            "policy",
            ["INITIAL_REQUEST_CONTRACT_FAILED"],
            ["request_context"],
            LIFECYCLE_FAILED,
            "Missing fields: %s" % ", ".join(missing),
        )
        next_state["lifecycle_status"] = LIFECYCLE_FAILED
        return next_state

    user_input = effective_user_input(next_state)
    normalized = {
        "symbol": str(user_input["symbol"]).upper(),
        "side": str(user_input["side"]).upper(),
        "type": str(user_input["type"]).upper(),
    }
    if "quoteOrderQty" in user_input:
        normalized["quoteOrderQty"] = str(user_input["quoteOrderQty"])
    if "quantity" in user_input:
        normalized["quantity"] = str(user_input["quantity"])
    next_state["normalized_order_intent"] = normalized
    next_state.setdefault("policy_context", {"policy_refs": []}).setdefault(
        "policy_refs", ["policy.symbol_allowlist", "policy.spot_testnet_only"]
    )
    if not next_state["policy_context"].get("policy_refs"):
        next_state["policy_context"]["policy_refs"] = ["policy.symbol_allowlist", "policy.spot_testnet_only"]
    append_check(next_state, "initial_request_contract", "policy", "pass", ["request_context"])
    append_check(next_state, "policy_context_available", "policy", "pass", ["policy_context.policy_refs[0]"])
    set_trace(
        next_state,
        "policy",
        ["ORDER_INTENT_NORMALIZED"],
        ["policy_context.policy_refs[0]"],
        PASS_ACTION,
    )
    return next_state
