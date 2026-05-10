"""Risk gate node — deterministic safety checks + mock tool calls."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from autocoin_ai.constants import (
    HOLD_DATA_INSUFFICIENT,
    HOLD_LOW_CONVICTION,
    HOLD_RISK_AGENT_FLAGGED,
    LIFECYCLE_FAILED,
    LIFECYCLE_HOLD,
    LIFECYCLE_NO_ORDER,
    LIFECYCLE_READY_FOR_BE,
    MAX_CONCENTRATION,
    PASS_ACTION,
    PERSONA_CONSERVATIVE,
    VOLATILITY_HIGH_THRESHOLD,
)
from autocoin_ai.models import AgentState, append_check, ensure_state_shape, set_trace
from autocoin_ai.tools.registry import dispatch


def risk_gate_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    lifecycle = next_state.get("lifecycle_status")
    if lifecycle == LIFECYCLE_FAILED:
        return next_state

    proposal = next_state.get("llm_proposal", {})
    intent = next_state.get("normalized_order_intent", {})
    bounds = next_state.get("policy_context", {}).get("persona_bounds", {})
    persona = next_state.get("inferred_persona", "MODERATE")
    tool_calls: list = list(next_state.get("risk_tool_calls", []))
    step = len(tool_calls) + 1

    action = str(proposal.get("action", ""))
    try:
        conviction = Decimal(str(proposal.get("conviction", 0)))
    except InvalidOperation:
        conviction = Decimal("0")

    try:
        size_usd = Decimal(str(proposal.get("size_usd") or intent.get("quoteOrderQty") or "0"))
    except InvalidOperation:
        size_usd = Decimal("0")

    symbol = str(intent.get("symbol", "")).upper()
    quote_asset = "USDT" if symbol.endswith("USDT") else symbol[-3:]
    max_order = Decimal(str(bounds.get("max_order_usd", 2000)))
    min_conviction = Decimal(str(bounds.get("min_conviction", 0.65)))
    allowed_symbols: list = bounds.get("allowed_symbols", [])

    # Check 1: action == HOLD
    if action == "HOLD":
        return _hold(next_state, tool_calls, "HOLD_ACTION", HOLD_LOW_CONVICTION)

    # Check 2: conviction too low
    if conviction < min_conviction:
        return _hold(next_state, tool_calls, "LOW_CONVICTION", HOLD_LOW_CONVICTION)

    # Check 3: size exceeds persona max
    if size_usd > max_order:
        return _no_order(next_state, tool_calls, "SIZE_EXCEEDS_PERSONA")

    # Check 4: symbol not in allowed list
    if allowed_symbols and symbol not in allowed_symbols:
        return _no_order(next_state, tool_calls, "SYMBOL_NOT_ALLOWED")

    # Check 5: balance check
    bal_result = dispatch("get_balance", {"asset": quote_asset})
    tool_calls.append({"step": step, "thought": "", "tool": "get_balance", "args": {"asset": quote_asset}, "result": bal_result})
    step += 1
    try:
        free_balance = Decimal(str(bal_result.get("free", "0")))
    except InvalidOperation:
        free_balance = Decimal("0")
    if free_balance < size_usd:
        return _hold(next_state, tool_calls, "INSUFFICIENT_BALANCE", HOLD_DATA_INSUFFICIENT)

    # Check 6: volatility check
    vol_result = dispatch("get_volatility", {"symbol": symbol, "days": 7})
    tool_calls.append({"step": step, "thought": "", "tool": "get_volatility", "args": {"symbol": symbol, "days": 7}, "result": vol_result})
    step += 1
    try:
        atr_pct = Decimal(str(vol_result.get("atr_pct", 0)))
    except InvalidOperation:
        atr_pct = Decimal("0")
    if atr_pct > Decimal(str(VOLATILITY_HIGH_THRESHOLD)):
        return _hold(next_state, tool_calls, "VOLATILITY_HIGH", HOLD_RISK_AGENT_FLAGGED)

    # Check 7: concentration risk (conservative only)
    if persona == PERSONA_CONSERVATIVE:
        conc_result = dispatch("get_concentration_risk", {"symbol": symbol, "proposed_size_usd": str(size_usd)})
        tool_calls.append({"step": step, "thought": "", "tool": "get_concentration_risk", "args": {"symbol": symbol, "proposed_size_usd": str(size_usd)}, "result": conc_result})
        try:
            conc_pct = Decimal(str(conc_result.get("concentration_pct", 0)))
        except InvalidOperation:
            conc_pct = Decimal("0")
        if conc_pct > Decimal(str(MAX_CONCENTRATION)):
            return _hold(next_state, tool_calls, "CONCENTRATION_HIGH", HOLD_RISK_AGENT_FLAGGED)

    # All checks passed
    next_state["risk_tool_calls"] = tool_calls
    tools_called = [t["tool"] for t in tool_calls]
    next_state["risk_assessment"] = {"verdict": "ALLOW", "fail_reason": None, "tools_called": tools_called}
    next_state["lifecycle_status"] = LIFECYCLE_READY_FOR_BE
    append_check(next_state, "risk_gate_verdict", "risk", "pass", ["risk_assessment"])
    set_trace(next_state, "risk", ["ALL_CHECKS_PASSED"], [t["tool"] for t in tool_calls] or ["risk_gate"], PASS_ACTION)
    return next_state


def _hold(state: AgentState, tool_calls: list, reason: str, hold_reason: str) -> AgentState:
    tools_called = [t["tool"] for t in tool_calls]
    state["risk_tool_calls"] = tool_calls
    state["risk_assessment"] = {"verdict": "HOLD", "fail_reason": reason, "tools_called": tools_called}
    state["lifecycle_status"] = LIFECYCLE_HOLD
    state["hold_reason"] = hold_reason
    append_check(state, "risk_gate_verdict", "risk", "fail", ["risk_assessment"])
    set_trace(state, "risk", [reason], ["risk_assessment"], LIFECYCLE_HOLD)
    return state


def _no_order(state: AgentState, tool_calls: list, reason: str) -> AgentState:
    tools_called = [t["tool"] for t in tool_calls]
    state["risk_tool_calls"] = tool_calls
    state["risk_assessment"] = {"verdict": "NO_ORDER", "fail_reason": reason, "tools_called": tools_called}
    state["lifecycle_status"] = LIFECYCLE_NO_ORDER
    state["hold_reason"] = None
    append_check(state, "risk_gate_verdict", "risk", "fail", ["risk_assessment"])
    set_trace(state, "risk", [reason], ["risk_assessment"], LIFECYCLE_NO_ORDER)
    return state
