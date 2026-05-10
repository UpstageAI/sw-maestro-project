"""Intake node — NL parsing or dict pass-through."""

from __future__ import annotations

from autocoin_ai.constants import (
    DEFAULT_TRADER,
    HOLD_INPUT_AMBIGUOUS,
    LIFECYCLE_FAILED,
    LIFECYCLE_HOLD,
    PERSONA_MODERATE,
)
from autocoin_ai.models import AgentState, append_check, ensure_state_shape, set_trace
from autocoin_ai.prompts.intake_prompt import INTAKE_SCHEMA, INTAKE_SYSTEM_INSTRUCTION
from autocoin_ai.llm import gemini_generate
from autocoin_ai.validators import validate_request_context


def intake_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    if next_state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return next_state

    request_context = next_state.get("request_context", {})
    user_input = request_context.get("user_input")

    if not isinstance(user_input, dict):
        _fail(next_state, "INITIAL_REQUEST_CONTRACT_FAILED", ["request_context.user_input"])
        return next_state

    text = user_input.get("text") or user_input.get("raw_text")
    if text:
        return _llm_mode(next_state, user_input, str(text))
    return _dict_mode(next_state, user_input)


def _llm_mode(state: AgentState, user_input: dict, text: str) -> AgentState:
    try:
        parsed = gemini_generate(text, INTAKE_SCHEMA, INTAKE_SYSTEM_INSTRUCTION)
    except Exception:
        _fail(state, "INTAKE_LLM_ERROR", ["request_context.user_input.text"])
        return state

    required = INTAKE_SCHEMA["required"]
    if not all(k in parsed for k in required):
        _fail(state, "INTAKE_SCHEMA_INVALID", ["llm_response"])
        return state

    ambiguity = parsed.get("ambiguity_score", 0)
    if ambiguity > 0.5:
        append_check(state, "intake_parse_complete", "intake", "fail", ["ambiguity_score"])
        set_trace(state, "intake", ["INPUT_AMBIGUOUS"], ["ambiguity_score"], LIFECYCLE_HOLD)
        state["lifecycle_status"] = LIFECYCLE_HOLD
        state["hold_reason"] = HOLD_INPUT_AMBIGUOUS
        return state

    trader_id = parsed.get("trader_id") or user_input.get("trader_id") or DEFAULT_TRADER
    _apply_parsed(state, parsed, trader_id, text)
    return state


def _dict_mode(state: AgentState, user_input: dict) -> AgentState:
    request_context = state.get("request_context", {})
    missing = validate_request_context(request_context)
    if missing:
        _fail(state, "INITIAL_REQUEST_CONTRACT_FAILED", ["request_context"])
        return state

    normalized = {
        "symbol": str(user_input["symbol"]).upper(),
        "side": str(user_input["side"]).upper(),
        "type": str(user_input["type"]).upper(),
    }
    if "quoteOrderQty" in user_input:
        normalized["quoteOrderQty"] = str(user_input["quoteOrderQty"])
    if "quantity" in user_input:
        normalized["quantity"] = str(user_input["quantity"])

    state["normalized_order_intent"] = normalized
    state["trader_id"] = str(user_input.get("trader_id") or DEFAULT_TRADER)
    state["inferred_persona"] = str(user_input.get("persona") or PERSONA_MODERATE)
    state["persona_override_reason"] = None

    append_check(state, "intake_parse_complete", "intake", "pass", ["normalized_order_intent"])
    set_trace(state, "intake", ["DICT_MODE_PASS"], ["request_context.user_input"], "PASS")
    return state


def _apply_parsed(state: AgentState, parsed: dict, trader_id: str, text: str) -> None:
    state["normalized_order_intent"] = {
        "symbol": str(parsed.get("symbol", "")).upper(),
        "side": str(parsed.get("side", "")).upper(),
        "type": str(parsed.get("type", "MARKET")).upper(),
        "quoteOrderQty": str(parsed.get("size_usd", "0")),
    }
    state["trader_id"] = trader_id
    state["inferred_persona"] = str(parsed.get("inferred_persona") or PERSONA_MODERATE)
    override = parsed.get("persona_override_reason")
    state["persona_override_reason"] = override if override else None

    append_check(state, "intake_parse_complete", "intake", "pass", ["normalized_order_intent"])
    set_trace(state, "intake", ["NL_PARSED"], ["request_context.user_input.text"], "PASS")


def _fail(state: AgentState, reason: str, evidence: list) -> None:
    append_check(state, "intake_parse_complete", "intake", "fail", evidence)
    set_trace(state, "intake", [reason], evidence, LIFECYCLE_FAILED)
    state["lifecycle_status"] = LIFECYCLE_FAILED
