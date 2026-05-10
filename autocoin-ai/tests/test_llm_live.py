"""Live Gemini LLM integration tests.

Run:  pytest tests/test_llm_live.py -v -m live
Skip: automatically skipped when GEMINI_API_KEY is absent.
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

HAVE_API_KEY = bool(os.getenv("GEMINI_API_KEY"))

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not HAVE_API_KEY, reason="GEMINI_API_KEY not set"),
]

import autocoin_ai.tools.account_tools  # noqa: E402 — register tools
import autocoin_ai.tools.market_tools  # noqa: E402
import autocoin_ai.tools.policy_tools  # noqa: E402


# ─── intake ────────────────────────────────────────────────────────────────

def test_intake_nl_parse_buy():
    """intake_node parses Korean NL text into BTCUSDT BUY intent."""
    from autocoin_ai.models import ensure_state_shape
    from autocoin_ai.nodes.intake import intake_node

    state = ensure_state_shape({
        "run_id": "live_intake_001",
        "request_context": {
            "request_id": "req_live_01",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-10T12:00:00+09:00",
            "user_input": {"text": "비트코인 100달러치 시장가로 매수하고 싶어", "trader_id": "wonyotti"},
        },
    })
    result = intake_node(state)

    intent = result.get("normalized_order_intent", {})
    assert "BTC" in str(intent.get("symbol", "")).upper()
    assert intent.get("side", "").upper() == "BUY"
    assert result.get("lifecycle_status") != "FAILED"


def test_intake_nl_parse_ambiguous():
    """intake_node flags ambiguous input (no symbol) with ambiguity_score > 0.5."""
    from autocoin_ai.constants import LIFECYCLE_HOLD
    from autocoin_ai.models import ensure_state_shape
    from autocoin_ai.nodes.intake import intake_node

    state = ensure_state_shape({
        "run_id": "live_intake_002",
        "request_context": {
            "request_id": "req_live_01b",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-10T12:00:00+09:00",
            "user_input": {"text": "그냥 좀 사줘", "trader_id": ""},
        },
    })
    result = intake_node(state)
    assert result.get("lifecycle_status") == LIFECYCLE_HOLD


# ─── strategy ──────────────────────────────────────────────────────────────

def test_strategy_generates_proposal():
    """strategy_node returns a structured BUY/SELL/HOLD proposal with conviction."""
    from autocoin_ai.models import ensure_state_shape, set_trace
    from autocoin_ai.nodes.strategy import strategy_node

    state = ensure_state_shape({
        "run_id": "live_strategy_001",
        "request_context": {
            "request_id": "req_live_02",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-10T12:00:00+09:00",
            "user_input": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET"},
        },
        "normalized_order_intent": {
            "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "100",
        },
        "inferred_persona": "MODERATE",
        "policy_context": {
            "policy_refs": ["policy.spot_testnet_only"],
            "persona_bounds": {"max_order_usd": 2000, "min_conviction": 0.65},
        },
        "trader_principles": [
            {"title": "추세 확인 후 진입", "preferred_action": "BUY on confirmed uptrend"},
            {"title": "손절 원칙", "preferred_action": "Set stop loss at -2%"},
        ],
    })
    set_trace(state, "intake", ["DICT_MODE_PASS"], ["user_input"], "PASS")
    set_trace(state, "policy", ["POLICY_PASS"], ["policy_context"], "PASS")

    result = strategy_node(state)

    proposal = result.get("llm_proposal", {})
    assert proposal.get("action") in ("BUY", "SELL", "HOLD")
    assert isinstance(proposal.get("conviction"), float)
    assert proposal.get("rationale")
    assert result.get("lifecycle_status") != "FAILED"


# ─── evaluator ─────────────────────────────────────────────────────────────

def test_evaluator_generates_report():
    """evaluator_node produces a user_message and reason_codes without fallback."""
    from autocoin_ai.constants import LIFECYCLE_READY_FOR_BE
    from autocoin_ai.models import append_check, ensure_state_shape, set_trace
    from autocoin_ai.nodes.evaluator import evaluator_node

    state = ensure_state_shape({
        "run_id": "live_eval_001",
        "request_context": {
            "request_id": "req_live_03",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-10T12:00:00+09:00",
            "user_input": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET"},
        },
        "lifecycle_status": LIFECYCLE_READY_FOR_BE,
        "normalized_order_intent": {
            "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "100",
        },
        "inferred_persona": "MODERATE",
        "llm_proposal": {
            "action": "BUY", "conviction": 0.75, "size_usd": "100",
            "rationale": "추세 확인 후 진입 원칙에 부합", "matched_principle_titles": [],
        },
        "risk_assessment": {
            "verdict": "ALLOW", "fail_reason": None,
            "tools_called": ["get_balance", "get_volatility"],
        },
        "risk_tool_calls": [
            {"step": 1, "thought": "", "tool": "get_balance",
             "args": {"asset": "USDT"}, "result": {"free": "500"}},
            {"step": 2, "thought": "", "tool": "get_volatility",
             "args": {"symbol": "BTCUSDT", "days": 7}, "result": {"atr_pct": "0.03"}},
        ],
        "policy_context": {"policy_refs": [], "persona_bounds": {}},
        "trader_principles": [],
    })
    set_trace(state, "intake", ["DICT_MODE_PASS"], ["user_input"], "PASS")
    set_trace(state, "policy", ["POLICY_PASS"], ["policy_context"], "PASS")
    set_trace(state, "strategy", ["BUY", "CONVICTION_0.75"], ["llm_proposal"], "BUY")
    set_trace(state, "risk", ["ALL_CHECKS_PASSED"], ["get_balance", "get_volatility"], LIFECYCLE_READY_FOR_BE)
    append_check(state, "strategy_proposal_generated", "strategy", "pass", ["llm_proposal"])

    result = evaluator_node(state)

    review = result.get("evaluator_review", {})
    assert review.get("user_message")
    assert review.get("summary")
    assert isinstance(review.get("reason_codes"), list)
    assert "EVALUATOR_LLM_FALLBACK" not in review.get("reason_codes", [])


# ─── risk_agent ReAct ───────────────────────────────────────────────────────

def test_risk_agent_react_loop():
    """risk_agent_node runs ReAct loop and records at least one tool call."""
    from autocoin_ai.models import ensure_state_shape, set_trace
    from autocoin_ai.nodes.risk_agent import risk_agent_node

    state = ensure_state_shape({
        "run_id": "live_risk_001",
        "request_context": {
            "request_id": "req_live_04",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-10T12:00:00+09:00",
            "user_input": {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET"},
        },
        "normalized_order_intent": {
            "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "100",
        },
        "inferred_persona": "MODERATE",
        "llm_proposal": {
            "action": "BUY", "conviction": 0.75, "size_usd": "100",
            "rationale": "추세 확인", "matched_principle_titles": [],
        },
        "policy_context": {
            "policy_refs": [],
            "persona_bounds": {"max_order_usd": 2000, "min_conviction": 0.65},
        },
    })
    set_trace(state, "intake", ["DICT_MODE_PASS"], ["user_input"], "PASS")
    set_trace(state, "policy", ["POLICY_PASS"], ["policy_context"], "PASS")
    set_trace(state, "strategy", ["BUY"], ["llm_proposal"], "BUY")

    result = risk_agent_node(state)

    tool_calls = result.get("risk_tool_calls", [])
    assert len(tool_calls) >= 1, "Expected at least one ReAct tool call"
    for call in tool_calls:
        assert "tool" in call
        assert "result" in call
