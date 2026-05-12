"""Strategy node — trader principles → trade proposal via LLM."""

from __future__ import annotations

from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_HOLD
from autocoin_ai.llm import gemini_generate
from autocoin_ai.models import AgentState, append_check, ensure_state_shape, set_trace
from autocoin_ai.prompts.strategy_prompt import STRATEGY_SCHEMA, STRATEGY_SYSTEM_INSTRUCTION


def strategy_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    lifecycle = next_state.get("lifecycle_status")
    if lifecycle in (LIFECYCLE_FAILED, LIFECYCLE_HOLD):
        return next_state

    intent = next_state.get("normalized_order_intent", {})
    principles = next_state.get("trader_principles", [])
    bounds = next_state.get("policy_context", {}).get("persona_bounds", {})
    persona = next_state.get("inferred_persona", "MODERATE")

    prompt = _build_prompt(intent, principles, bounds, persona)

    try:
        response = gemini_generate(prompt, STRATEGY_SCHEMA, STRATEGY_SYSTEM_INSTRUCTION)
    except Exception:
        _fail(next_state, "STRATEGY_LLM_ERROR", ["gemini_generate"])
        return next_state

    required = STRATEGY_SCHEMA["required"]
    if not all(k in response for k in required):
        _fail(next_state, "STRATEGY_LLM_ERROR", ["llm_response"])
        return next_state

    # Validate matched_principle_titles against actual principles
    valid_titles = {p["title"] for p in principles if isinstance(p, dict) and "title" in p}
    matched = response.get("matched_principle_titles", [])
    hallucinated = [t for t in matched if t not in valid_titles]
    if hallucinated:
        response = dict(response)
        response["schema_warning"] = "Hallucinated principle titles: %s" % hallucinated

    next_state["llm_proposal"] = response

    action = str(response.get("action", ""))
    conviction = float(response.get("conviction", 0))
    rationale = str(response.get("rationale", ""))

    append_check(
        next_state,
        "strategy_proposal_generated",
        "strategy",
        "pass",
        ["llm_proposal"],
    )
    set_trace(
        next_state,
        "strategy",
        [action, "CONVICTION_%.2f" % conviction],
        matched or ["llm_proposal"],
        action,
        rationale,
    )
    return next_state


def _build_prompt(intent: dict, principles: list, bounds: dict, persona: str) -> str:
    principle_lines = "\n".join(
        "- %s: %s" % (p.get("title", ""), p.get("preferred_action", ""))
        for p in principles
        if isinstance(p, dict)
    )
    return (
        "Order intent: symbol=%s side=%s type=%s size=%s\n"
        "Persona: %s (max_order_usd=%.0f, min_conviction=%.2f)\n"
        "Trader principles:\n%s"
    ) % (
        intent.get("symbol", ""),
        intent.get("side", ""),
        intent.get("type", ""),
        intent.get("quoteOrderQty", intent.get("size_usd", "0")),
        persona,
        float(bounds.get("max_order_usd", 2000)),
        float(bounds.get("min_conviction", 0.65)),
        principle_lines or "(no principles loaded)",
    )


def _fail(state: AgentState, reason: str, evidence: list) -> None:
    append_check(state, "strategy_proposal_generated", "strategy", "fail", evidence)
    set_trace(state, "strategy", [reason], evidence, LIFECYCLE_FAILED)
    state["lifecycle_status"] = LIFECYCLE_FAILED
