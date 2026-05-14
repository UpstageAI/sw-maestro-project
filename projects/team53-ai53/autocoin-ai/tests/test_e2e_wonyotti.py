"""E2E tests for wonyotti trader scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import autocoin_ai.tools.account_tools  # register tools
import autocoin_ai.tools.market_tools
import autocoin_ai.tools.policy_tools

from autocoin_ai.constants import HOLD_LOW_CONVICTION, LIFECYCLE_HOLD, LIFECYCLE_READY_FOR_BE
from autocoin_ai.graph import build_agentic_order_graph
from autocoin_ai.llm import StepResult
from autocoin_ai.models import ensure_state_shape

_NOOP_STEP = StepResult(is_final=True, function_calls=[], text="", candidate_content=None)

EXAMPLES = Path(__file__).parent.parent / "examples"

EVAL_RESP = {
    "summary": "BTC 매수 평가 완료.",
    "user_message": "매수 주문이 승인되었습니다. 리스크 검사를 통과하였습니다. 주문 실행 준비가 되었습니다.",
    "reason_codes": ["RISK_GATE_PASSED"],
    "schema_warnings": [],
}

EVAL_HOLD_RESP = {
    "summary": "낮은 확신으로 홀드.",
    "user_message": "확신이 부족하여 홀드 결정이 내려졌습니다. 시장 상황을 재확인하세요.",
    "reason_codes": ["HOLD_LOW_CONVICTION"],
    "schema_warnings": [],
}


def _run(example_file: str) -> dict:
    state = json.loads((EXAMPLES / example_file).read_text())
    return ensure_state_shape(state)


def test_e2e_wonyotti_buy():
    state = _run("wonyotti_buy.json")
    strategy_resp = {
        "action": "BUY",
        "size_usd": "100",
        "conviction": 0.80,
        "rationale": "추세 확인 후 매수 원칙에 부합.",
        "matched_principle_titles": [],
    }
    graph = build_agentic_order_graph()
    with patch("autocoin_ai.nodes.strategy.gemini_generate", return_value=strategy_resp), \
         patch("autocoin_ai.nodes.risk_agent.gemini_step_with_tools", return_value=_NOOP_STEP), \
         patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=EVAL_RESP):
        result = graph.invoke(state, config={"configurable": {"thread_id": state["run_id"]}})

    assert result["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert result["evaluator_review"]["user_message"] is not None
    assert result["decision_trace"]["evaluator"]["final_action"] == "PASS"
    assert result["decision_trace"]["run_summary"]["reason_codes"] == ["RUN_COMPLETE"]


def test_e2e_wonyotti_hold():
    state = _run("wonyotti_hold_low_conviction.json")
    strategy_resp = {
        "action": "BUY",
        "size_usd": "100",
        "conviction": 0.40,
        "rationale": "추세 불명확, 확신 낮음.",
        "matched_principle_titles": [],
    }
    graph = build_agentic_order_graph()
    with patch("autocoin_ai.nodes.strategy.gemini_generate", return_value=strategy_resp), \
         patch("autocoin_ai.nodes.risk_agent.gemini_step_with_tools", return_value=_NOOP_STEP), \
         patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=EVAL_HOLD_RESP):
        result = graph.invoke(state, config={"configurable": {"thread_id": state["run_id"]}})

    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_LOW_CONVICTION
    assert result["evaluator_review"]["user_message"] is not None
