"""Tests for evaluator_node (Phase 3b-2)."""

from __future__ import annotations

from unittest.mock import patch

from autocoin_ai.constants import (
    HOLD_LOW_CONVICTION,
    LIFECYCLE_FAILED,
    LIFECYCLE_HOLD,
    LIFECYCLE_NO_ORDER,
    LIFECYCLE_READY_FOR_BE,
)
from autocoin_ai.models import AgentState, ensure_state_shape
from autocoin_ai.nodes.evaluator import evaluator_node

MOCK_LLM_RESP = {
    "summary": "BTC 100 USDT 매수 평가 완료.",
    "user_message": "매수 주문이 승인되었습니다. 리스크 점검을 통과하였으며 주문 실행 준비가 되었습니다.",
    "reason_codes": ["EVIDENCE_SUMMARIZED", "RISK_GATE_PASSED"],
    "schema_warnings": [],
}


def _base_state(lifecycle: str, extra: dict | None = None) -> AgentState:
    state = {
        "run_id": "test_eval",
        "request_context": {
            "request_id": "r1",
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
        "lifecycle_status": lifecycle,
        "llm_proposal": {
            "action": "BUY",
            "size_usd": "100",
            "conviction": 0.80,
            "rationale": "추세 확인.",
            "matched_principle_titles": ["추세 확인 후 진입"],
        },
        "trader_principles": [
            {"title": "추세 확인 후 진입", "chunk_id": "w.trend", "content": "", "keywords": ["trend"],
             "preferred_action": "BUY in uptrend", "avoid_when": "", "source_refs": []},
        ],
        "risk_assessment": {"verdict": "ALLOW", "fail_reason": None, "tools_called": ["get_balance", "get_volatility"]},
        "risk_tool_calls": [
            {"step": 1, "tool": "get_balance", "args": {}, "result": {}, "thought": ""},
            {"step": 2, "tool": "get_volatility", "args": {}, "result": {}, "thought": ""},
        ],
        "verification_checks": [
            {"name": "policy_grounded", "stage": "policy", "result": "pass", "evidence_refs": ["policy_context"]},
            {"name": "strategy_proposal_generated", "stage": "strategy", "result": "pass", "evidence_refs": ["llm_proposal"]},
            {"name": "risk_gate_verdict", "stage": "risk", "result": "pass", "evidence_refs": ["risk_assessment"]},
        ],
        "decision_trace": {
            "intake": {"reason_codes": ["PARSED"], "evidence_refs": ["normalized_order_intent"], "final_action": "PASS"},
            "policy": {"reason_codes": ["POLICY_GROUNDED"], "evidence_refs": ["policy_context"], "final_action": "PASS"},
            "strategy": {"reason_codes": ["BUY"], "evidence_refs": ["llm_proposal"], "final_action": "BUY"},
            "risk": {"reason_codes": ["ALL_CHECKS_PASSED"], "evidence_refs": ["risk_assessment"], "final_action": "PASS"},
            "evaluator": {},
            "execution": {},
            "run_summary": {},
        },
    }
    if extra:
        state.update(extra)
    return ensure_state_shape(state)


def _non_agentic_state(lifecycle: str, extra: dict | None = None) -> AgentState:
    state = _base_state(
        lifecycle,
        {
            "trader_id": "",
            "llm_proposal": {},
            "risk_tool_calls": [],
            "risk_assessment": {"verdict": "ALLOW", "fail_reason": None, "tools_called": []},
            "verification_checks": [
                {"name": "initial_request_contract", "stage": "policy", "result": "pass", "evidence_refs": ["request_context"]},
                {"name": "policy_context_available", "stage": "policy", "result": "pass", "evidence_refs": ["policy_context.policy_refs[0]"]},
                {"name": "policy_context_grounded", "stage": "policy", "result": "pass", "evidence_refs": ["trader_principles"]},
                {"name": "risk_gate_rules", "stage": "risk", "result": "pass", "evidence_refs": ["normalized_order_intent"]},
            ],
            "decision_trace": {
                "intake": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
                "policy": {"reason_codes": ["ORDER_INTENT_NORMALIZED", "POLICY_GROUNDED"], "evidence_refs": ["policy_context.policy_refs[0]", "trader_principles"], "final_action": "PASS"},
                "strategy": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
                "risk": {"reason_codes": ["ALL_CHECKS_PASSED"], "evidence_refs": ["verification_checks[-1]"], "final_action": "PASS"},
                "evaluator": {},
                "execution": {},
                "run_summary": {},
            },
        },
    )
    if extra:
        state.update(extra)
    return ensure_state_shape(state)


def test_evaluator_ready_for_be():
    state = _base_state(LIFECYCLE_READY_FOR_BE)
    with patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=MOCK_LLM_RESP):
        result = evaluator_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert result["evaluator_review"]["summary"] == MOCK_LLM_RESP["summary"]
    assert result["evaluator_review"]["user_message"] == MOCK_LLM_RESP["user_message"]
    assert result["decision_trace"]["evaluator"]["final_action"] == "PASS"
    assert result["decision_trace"]["run_summary"]["reason_codes"] == ["RUN_COMPLETE"]
    assert any(c["name"] == "evaluator_summary_complete" for c in result["verification_checks"])


def test_evaluator_hold_summary():
    state = _base_state(LIFECYCLE_HOLD, {"hold_reason": HOLD_LOW_CONVICTION})
    state["risk_assessment"] = {"verdict": "HOLD", "fail_reason": "LOW_CONVICTION", "tools_called": []}
    state["risk_tool_calls"] = []
    hold_resp = dict(MOCK_LLM_RESP, summary="낮은 확신으로 홀드.", reason_codes=["HOLD_LOW_CONVICTION"])
    with patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=hold_resp):
        result = evaluator_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["evaluator_review"]["user_message"] is not None
    assert result["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_HOLD


def test_evaluator_no_order_summary():
    state = _base_state(LIFECYCLE_NO_ORDER)
    state["risk_assessment"] = {"verdict": "NO_ORDER", "fail_reason": "SIZE_EXCEEDS_PERSONA", "tools_called": []}
    state["risk_tool_calls"] = []
    no_order_resp = dict(MOCK_LLM_RESP, reason_codes=["NO_ORDER_GENERATED"])
    with patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=no_order_resp):
        result = evaluator_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_NO_ORDER
    assert result["evaluator_review"] is not None
    assert result["decision_trace"]["evaluator"]["final_action"] == LIFECYCLE_NO_ORDER


def test_evaluator_llm_fallback():
    state = _base_state(LIFECYCLE_READY_FOR_BE)
    with patch("autocoin_ai.nodes.evaluator.gemini_generate", side_effect=RuntimeError("LLM down")):
        result = evaluator_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert "EVALUATOR_LLM_FALLBACK" in result["evaluator_review"]["reason_codes"]
    assert "LLM call failed" in result["evaluator_review"]["schema_warnings"][0]


def test_evaluator_skips_failed():
    state = _base_state(LIFECYCLE_FAILED)
    result = evaluator_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_FAILED
    assert result.get("evaluator_review", {}) == {}


def test_evaluator_non_agentic_hold_does_not_require_agentic_stages():
    state = _non_agentic_state(
        LIFECYCLE_HOLD,
        {
            "hold_reason": HOLD_LOW_CONVICTION,
            "risk_assessment": {"verdict": "HOLD", "fail_reason": "LOW_CONVICTION", "tools_called": []},
            "decision_trace": {
                "intake": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
                "policy": {"reason_codes": ["ORDER_INTENT_NORMALIZED", "POLICY_GROUNDED"], "evidence_refs": ["policy_context.policy_refs[0]", "trader_principles"], "final_action": "PASS"},
                "strategy": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
                "risk": {"reason_codes": ["LOW_CONVICTION"], "evidence_refs": ["verification_checks[-1]"], "final_action": LIFECYCLE_HOLD},
                "evaluator": {},
                "execution": {},
                "run_summary": {},
            },
        },
    )
    hold_resp = dict(MOCK_LLM_RESP, summary="낮은 확신으로 홀드.", reason_codes=["HOLD_LOW_CONVICTION"])

    with patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=hold_resp):
        result = evaluator_node(state)

    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["evaluator_review"]["schema_warnings"] == []
    assert result["decision_trace"]["evaluator"]["final_action"] == LIFECYCLE_HOLD
