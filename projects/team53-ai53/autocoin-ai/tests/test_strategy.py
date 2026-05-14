"""Tests for strategy_node."""

from __future__ import annotations

from unittest.mock import patch

from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_HOLD
from autocoin_ai.models import ensure_state_shape
from autocoin_ai.nodes.strategy import strategy_node

PRINCIPLES = [
    {"chunk_id": "w.risk_first", "title": "리스크 관리 최우선", "content": "", "keywords": ["risk"], "preferred_action": "reduce size", "avoid_when": "", "source_refs": []},
    {"chunk_id": "w.trend", "title": "추세 확인 후 진입", "content": "", "keywords": ["trend"], "preferred_action": "BUY in uptrend", "avoid_when": "", "source_refs": []},
]

BASE_STATE = {
    "run_id": "test_strategy",
    "request_context": {
        "request_id": "req_strat",
        "request_type": "PLACE_ORDER_TEST",
        "requested_at": "2026-05-10T10:00:00+09:00",
        "user_input": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "100"},
    },
    "policy_context": {
        "policy_refs": ["policy.spot_testnet_only"],
        "persona": "MODERATE",
        "persona_bounds": {"max_order_usd": 2000.0, "min_conviction": 0.65},
    },
    "normalized_order_intent": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "100"},
    "inferred_persona": "MODERATE",
}


def _make_state(extra: dict | None = None) -> dict:
    base = dict(BASE_STATE)
    base["trader_principles"] = list(PRINCIPLES)
    if extra:
        base.update(extra)
    return ensure_state_shape(base)


def test_strategy_buy_proposal():
    mock_resp = {
        "action": "BUY",
        "size_usd": "100",
        "conviction": 0.80,
        "rationale": "추세 확인 후 진입 원칙에 부합.",
        "matched_principle_titles": ["추세 확인 후 진입"],
    }
    with patch("autocoin_ai.nodes.strategy.gemini_generate", return_value=mock_resp):
        result = strategy_node(_make_state())
    assert result["lifecycle_status"] != LIFECYCLE_FAILED
    assert result["llm_proposal"]["action"] == "BUY"
    assert result["llm_proposal"]["conviction"] == 0.80
    assert result["decision_trace"]["strategy"]["final_action"] == "BUY"


def test_strategy_hold_action():
    mock_resp = {
        "action": "HOLD",
        "size_usd": "0",
        "conviction": 0.3,
        "rationale": "추세 불명확. 대기.",
        "matched_principle_titles": ["리스크 관리 최우선"],
    }
    with patch("autocoin_ai.nodes.strategy.gemini_generate", return_value=mock_resp):
        result = strategy_node(_make_state())
    assert result["llm_proposal"]["action"] == "HOLD"
    assert result["decision_trace"]["strategy"]["final_action"] == "HOLD"


def test_strategy_passes_failed():
    state = _make_state({"lifecycle_status": LIFECYCLE_FAILED})
    result = strategy_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_FAILED
    assert result["decision_trace"]["strategy"]["final_action"] == ""


def test_strategy_passes_hold():
    state = _make_state({"lifecycle_status": LIFECYCLE_HOLD})
    result = strategy_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["decision_trace"]["strategy"]["final_action"] == ""


def test_strategy_invalid_principles():
    mock_resp = {
        "action": "BUY",
        "size_usd": "100",
        "conviction": 0.75,
        "rationale": "원칙 기반 매수.",
        "matched_principle_titles": ["존재하지 않는 원칙 제목"],
    }
    with patch("autocoin_ai.nodes.strategy.gemini_generate", return_value=mock_resp):
        result = strategy_node(_make_state())
    assert "schema_warning" in result["llm_proposal"]
    assert "존재하지 않는 원칙 제목" in result["llm_proposal"]["schema_warning"]
