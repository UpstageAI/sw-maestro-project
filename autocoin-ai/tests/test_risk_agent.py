"""Tests for risk_agent_node (Phase 3c)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import autocoin_ai.tools.account_tools  # register tools
import autocoin_ai.tools.market_tools
import autocoin_ai.tools.policy_tools
from autocoin_ai.constants import MAX_TOOL_CALLS
from autocoin_ai.llm import StepResult
from autocoin_ai.models import ensure_state_shape
from autocoin_ai.nodes.risk_agent import risk_agent_node


def _mock_fc(name: str, args: dict) -> MagicMock:
    fc = MagicMock()
    fc.name = name
    fc.args = args
    return fc


def _base_state() -> dict:
    return ensure_state_shape({
        "run_id": "test_ra",
        "request_context": {
            "request_id": "r1",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-10T10:00:00+09:00",
            "user_input": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "100"},
        },
        "policy_context": {
            "policy_refs": ["policy.spot_testnet_only"],
            "persona": "MODERATE",
            "persona_bounds": {"max_order_usd": 2000.0, "min_conviction": 0.65, "allowed_symbols": ["BTCUSDT"]},
        },
        "normalized_order_intent": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "100"},
        "inferred_persona": "MODERATE",
        "llm_proposal": {"action": "BUY", "size_usd": "100", "conviction": 0.80, "matched_principle_titles": []},
    })


def test_risk_agent_records_tool_calls_with_thought():
    step1 = StepResult(
        is_final=False,
        function_calls=[
            _mock_fc("get_balance", {"asset": "USDT"}),
            _mock_fc("get_volatility", {"symbol": "BTCUSDT", "days": 7}),
        ],
        text="Checking account balance and volatility.",
        candidate_content=None,
    )
    step2 = StepResult(is_final=True, function_calls=[], text="Assessment complete.", candidate_content=None)

    with patch("autocoin_ai.nodes.risk_agent.gemini_step_with_tools", side_effect=[step1, step2]):
        result = risk_agent_node(_base_state())

    calls = result["risk_tool_calls"]
    assert len(calls) == 2
    assert calls[0]["tool"] == "get_balance"
    assert calls[1]["tool"] == "get_volatility"
    assert calls[0]["thought"] == "Checking account balance and volatility."
    assert "free" in calls[0]["result"]
    assert "atr_pct" in calls[1]["result"]


def test_risk_agent_respects_max_tool_calls():
    always_call = StepResult(
        is_final=False,
        function_calls=[_mock_fc("get_balance", {"asset": "USDT"})],
        text="",
        candidate_content=None,
    )
    with patch("autocoin_ai.nodes.risk_agent.gemini_step_with_tools", return_value=always_call):
        result = risk_agent_node(_base_state())

    assert len(result["risk_tool_calls"]) <= MAX_TOOL_CALLS
