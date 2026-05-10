"""Tests for intake_node."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from autocoin_ai.constants import (
    HOLD_INPUT_AMBIGUOUS,
    LIFECYCLE_FAILED,
    LIFECYCLE_HOLD,
)
from autocoin_ai.models import ensure_state_shape
from autocoin_ai.nodes.intake import intake_node

BASE_REQUEST_CONTEXT = {
    "request_id": "req_test_001",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T10:00:00+09:00",
    "user_input": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": "50",
    },
}

POLICY_CONTEXT = {"policy_refs": ["policy.spot_testnet_only"]}


def _make_state(user_input: dict) -> dict:
    return ensure_state_shape({
        "run_id": "test_run",
        "request_context": {
            "request_id": "req_test_001",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-10T10:00:00+09:00",
            "user_input": user_input,
        },
        "policy_context": POLICY_CONTEXT,
    })


def test_intake_dict_legacy():
    state = _make_state({
        "symbol": "BTCUSDT",
        "side": "buy",
        "type": "market",
        "quoteOrderQty": "100",
    })
    result = intake_node(state)
    assert result["lifecycle_status"] != LIFECYCLE_FAILED
    assert result["normalized_order_intent"]["symbol"] == "BTCUSDT"
    assert result["normalized_order_intent"]["side"] == "BUY"
    assert result["normalized_order_intent"]["type"] == "MARKET"
    assert result["trader_id"] == "wonyotti"
    assert result["inferred_persona"] == "MODERATE"


def test_intake_missing_fields():
    state = _make_state({"symbol": "BTCUSDT"})
    result = intake_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_FAILED
    checks = [c for c in result["verification_checks"] if c["stage"] == "intake"]
    assert any(c["result"] == "fail" for c in checks)


def test_intake_text_ambiguous():
    mock_response = {
        "symbol": "",
        "side": "BUY",
        "type": "MARKET",
        "size_usd": "0",
        "trader_id": "",
        "inferred_persona": "MODERATE",
        "persona_override_reason": "",
        "ambiguity_score": 0.9,
    }
    state = _make_state({"text": "비트코인 좀 사봐"})
    with patch("autocoin_ai.nodes.intake.gemini_generate", return_value=mock_response):
        result = intake_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_INPUT_AMBIGUOUS


def test_intake_text_buy():
    mock_response = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "size_usd": "37.04",
        "trader_id": "wonyotti",
        "inferred_persona": "MODERATE",
        "persona_override_reason": "",
        "ambiguity_score": 0.1,
    }
    state = _make_state({"text": "BTC 5만원치 사줘", "trader_id": "wonyotti"})
    with patch("autocoin_ai.nodes.intake.gemini_generate", return_value=mock_response):
        result = intake_node(state)
    assert result["lifecycle_status"] != LIFECYCLE_FAILED
    assert result["lifecycle_status"] != LIFECYCLE_HOLD
    assert result["normalized_order_intent"]["symbol"] == "BTCUSDT"
    assert result["normalized_order_intent"]["side"] == "BUY"
    assert result["trader_id"] == "wonyotti"
