"""Policy / planning node."""

from __future__ import annotations

import dataclasses

from autocoin_ai.constants import DEFAULT_TRADER, LIFECYCLE_FAILED, PASS_ACTION, PERSONA_MODERATE
from autocoin_ai.models import AgentState, append_check, effective_user_input, ensure_state_shape, set_trace
from autocoin_ai.personas import PERSONA_PROFILES
from autocoin_ai.rag.retriever import retrieve_relevant
from autocoin_ai.validators import validate_policy_context, validate_request_context


def policy_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)

    if next_state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return next_state

    # If intake already ran, normalized_order_intent is already set — skip re-validation.
    already_normalized = bool(next_state.get("normalized_order_intent"))

    if not already_normalized:
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
        append_check(next_state, "initial_request_contract", "policy", "pass", ["request_context"])

    policy_missing = validate_policy_context(next_state.get("policy_context", {}))
    if policy_missing:
        append_check(next_state, "policy_context_contract", "policy", "fail", ["policy_context"])
        set_trace(
            next_state,
            "policy",
            ["POLICY_CONTEXT_MISSING"],
            ["policy_context"],
            LIFECYCLE_FAILED,
            "Missing fields: %s" % ", ".join(policy_missing),
        )
        next_state["lifecycle_status"] = LIFECYCLE_FAILED
        return next_state

    # RAG grounding
    intent = next_state.get("normalized_order_intent", {})
    trader_id = next_state.get("trader_id") or DEFAULT_TRADER
    persona = next_state.get("inferred_persona") or PERSONA_MODERATE

    policy_context = dict(next_state.get("policy_context", {}))
    policy_context["persona"] = persona
    policy_context["persona_bounds"] = PERSONA_PROFILES.get(persona, PERSONA_PROFILES[PERSONA_MODERATE])
    next_state["policy_context"] = policy_context

    query = "%s %s %s" % (intent.get("symbol", ""), intent.get("side", ""), persona)
    principles = retrieve_relevant(trader_id, query, k=5)
    next_state["trader_principles"] = [dataclasses.asdict(p) for p in principles]

    append_check(next_state, "policy_context_available", "policy", "pass", ["policy_context.policy_refs[0]"])
    append_check(next_state, "policy_context_grounded", "policy", "pass", ["trader_principles"])
    set_trace(
        next_state,
        "policy",
        ["ORDER_INTENT_NORMALIZED", "POLICY_GROUNDED"],
        ["policy_context.policy_refs[0]", "trader_principles"],
        PASS_ACTION,
    )
    return next_state
