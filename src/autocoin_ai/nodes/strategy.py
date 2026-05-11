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
    request_context = next_state.get("request_context", {})
    user_input = request_context.get("user_input", {}) if isinstance(request_context, dict) else {}
    market_snapshot = user_input.get("market_snapshot", {}) if isinstance(user_input, dict) else {}
    account_balance = user_input.get("account_balance", {}) if isinstance(user_input, dict) else {}

    prompt = _build_prompt(intent, principles, bounds, persona, market_snapshot, account_balance)

    try:
        response = gemini_generate(prompt, STRATEGY_SCHEMA, STRATEGY_SYSTEM_INSTRUCTION)
    except Exception:
        fallback = _fallback_proposal(intent, principles, bounds, persona)
        if fallback is None:
            _fail(next_state, "STRATEGY_LLM_ERROR", ["gemini_generate"])
            return next_state
        response = fallback

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


def _build_prompt(intent: dict, principles: list, bounds: dict, persona: str, market_snapshot: dict, account_balance: dict) -> str:
    principle_lines = "\n".join(
        "- %s: %s" % (p.get("title", ""), p.get("preferred_action", ""))
        for p in principles
        if isinstance(p, dict)
    )

    price_snapshot = market_snapshot.get("price", {}) if isinstance(market_snapshot, dict) else {}
    latest_price = price_snapshot.get("price", "unknown")
    captured_at = market_snapshot.get("capturedAt", "unknown") if isinstance(market_snapshot, dict) else "unknown"
    balances = account_balance.get("balances", []) if isinstance(account_balance, dict) else []
    balance_summary = ", ".join(
        "%s free=%s locked=%s" % (b.get("asset", ""), b.get("free", "0"), b.get("locked", "0"))
        for b in balances[:4]
        if isinstance(b, dict)
    )
    return (
        "Order intent: symbol=%s side=%s type=%s size=%s\n"
        "Live market snapshot: price=%s captured_at=%s\n"
        "Live account snapshot: %s\n"
        "Persona: %s (max_order_usd=%.0f, min_conviction=%.2f)\n"
        "Trader principles:\n%s\n"
        "When user intent is explicit and live snapshots do not show a clear contradiction, prefer following the intent over HOLD."
    ) % (
        intent.get("symbol", ""),
        intent.get("side", ""),
        intent.get("type", ""),
        intent.get("quoteOrderQty", intent.get("size_usd", "0")),
        latest_price,
        captured_at,
        balance_summary or "no live balances provided",
        persona,
        float(bounds.get("max_order_usd", 2000)),
        float(bounds.get("min_conviction", 0.65)),
        principle_lines or "(no principles loaded)",
    )


def _fallback_proposal(intent: dict, principles: list, bounds: dict, persona: str) -> dict | None:
    symbol = str(intent.get("symbol", "")).upper()
    side = str(intent.get("side", "")).upper()
    size_usd = str(intent.get("quoteOrderQty") or intent.get("size_usd") or "")

    if not symbol or side not in {"BUY", "SELL"} or not size_usd:
        return None

    try:
        min_conviction = float(bounds.get("min_conviction", 0.65))
    except (TypeError, ValueError):
        min_conviction = 0.65
    conviction = max(min_conviction + 0.05, 0.70)

    matched_titles = [
        str(principles[0].get("title", ""))
        for _ in [0]
        if principles and isinstance(principles[0], dict) and principles[0].get("title")
    ]

    return {
        "action": side,
        "size_usd": size_usd,
        "conviction": round(min(conviction, 0.90), 2),
        "rationale": "%s persona의 기본 bounds 안에서 사용자의 명시적 %s 의도를 우선 실행 후보로 유지합니다." % (persona, side),
        "matched_principle_titles": matched_titles,
    }


def _fail(state: AgentState, reason: str, evidence: list) -> None:
    append_check(state, "strategy_proposal_generated", "strategy", "fail", evidence)
    set_trace(state, "strategy", [reason], evidence, LIFECYCLE_FAILED)
    state["lifecycle_status"] = LIFECYCLE_FAILED
