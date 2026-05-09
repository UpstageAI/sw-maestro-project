"""Tests for risk_gate_node."""

from __future__ import annotations

import autocoin_ai.tools.account_tools  # register tools
import autocoin_ai.tools.market_tools
import autocoin_ai.tools.policy_tools
from autocoin_ai.constants import (
    HOLD_DATA_INSUFFICIENT,
    HOLD_LOW_CONVICTION,
    HOLD_RISK_AGENT_FLAGGED,
    LIFECYCLE_HOLD,
    LIFECYCLE_NO_ORDER,
    LIFECYCLE_READY_FOR_BE,
)
from autocoin_ai.models import ensure_state_shape
from autocoin_ai.nodes.risk_gate import risk_gate_node

PERSONA_MODERATE_BOUNDS = {
    "max_order_usd": 2000.0,
    "min_conviction": 0.65,
    "allowed_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
}


def _make_state(proposal: dict, symbol: str = "BTCUSDT", extra: dict | None = None) -> dict:
    state = {
        "run_id": "test_rg",
        "request_context": {
            "request_id": "r1",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-10T10:00:00+09:00",
            "user_input": {"symbol": symbol, "side": "BUY", "type": "MARKET", "quoteOrderQty": proposal.get("size_usd", "100")},
        },
        "policy_context": {
            "policy_refs": ["policy.spot_testnet_only"],
            "persona": "MODERATE",
            "persona_bounds": PERSONA_MODERATE_BOUNDS,
        },
        "normalized_order_intent": {"symbol": symbol, "side": "BUY", "type": "MARKET", "quoteOrderQty": proposal.get("size_usd", "100")},
        "inferred_persona": "MODERATE",
        "llm_proposal": proposal,
    }
    if extra:
        state.update(extra)
    return ensure_state_shape(state)


def test_risk_gate_pass():
    proposal = {"action": "BUY", "size_usd": "100", "conviction": 0.80, "matched_principle_titles": []}
    result = risk_gate_node(_make_state(proposal))
    assert result["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert result["risk_assessment"]["verdict"] == "ALLOW"
    assert "get_balance" in result["risk_assessment"]["tools_called"]
    assert "get_volatility" in result["risk_assessment"]["tools_called"]


def test_risk_gate_low_conviction():
    proposal = {"action": "BUY", "size_usd": "100", "conviction": 0.40, "matched_principle_titles": []}
    result = risk_gate_node(_make_state(proposal))
    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_LOW_CONVICTION


def test_risk_gate_hold_action():
    proposal = {"action": "HOLD", "size_usd": "0", "conviction": 0.80, "matched_principle_titles": []}
    result = risk_gate_node(_make_state(proposal))
    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_LOW_CONVICTION


def test_risk_gate_size_exceeds():
    proposal = {"action": "BUY", "size_usd": "5000", "conviction": 0.80, "matched_principle_titles": []}
    result = risk_gate_node(_make_state(proposal))
    assert result["lifecycle_status"] == LIFECYCLE_NO_ORDER
    assert result["risk_assessment"]["fail_reason"] == "SIZE_EXCEEDS_PERSONA"


def test_risk_gate_symbol_blocked():
    proposal = {"action": "BUY", "size_usd": "100", "conviction": 0.80, "matched_principle_titles": []}
    result = risk_gate_node(_make_state(proposal, symbol="DOGEUSDT"))
    assert result["lifecycle_status"] == LIFECYCLE_NO_ORDER
    assert result["risk_assessment"]["fail_reason"] == "SYMBOL_NOT_ALLOWED"


def test_risk_gate_balance_short():
    # size_usd > free balance (5000 USDT in mock)
    proposal = {"action": "BUY", "size_usd": "9999", "conviction": 0.80, "matched_principle_titles": []}
    bounds = dict(PERSONA_MODERATE_BOUNDS)
    bounds["max_order_usd"] = 99999.0  # allow large order to reach balance check
    state = _make_state(proposal)
    state["policy_context"]["persona_bounds"] = bounds
    result = risk_gate_node(ensure_state_shape(state))
    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_DATA_INSUFFICIENT


def test_risk_gate_volatility_high():
    # DOGEUSDT has atr_pct=0.12 > 0.08 — but DOGE is not in allowed list for MODERATE
    # Use a symbol with high volatility that IS allowed... but mock only has DOGE as high.
    # Override allowed_symbols to include DOGEUSDT for this test.
    proposal = {"action": "BUY", "size_usd": "100", "conviction": 0.80, "matched_principle_titles": []}
    state = _make_state(proposal, symbol="DOGEUSDT")
    bounds = dict(PERSONA_MODERATE_BOUNDS)
    bounds["allowed_symbols"] = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "DOGEUSDT"]  # allow DOGE
    state["policy_context"]["persona_bounds"] = bounds
    state["normalized_order_intent"]["symbol"] = "DOGEUSDT"
    result = risk_gate_node(ensure_state_shape(state))
    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_RISK_AGENT_FLAGGED
    assert result["risk_assessment"]["fail_reason"] == "VOLATILITY_HIGH"
