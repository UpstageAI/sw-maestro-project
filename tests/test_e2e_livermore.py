"""E2E tests for livermore trader + ambiguous input scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import autocoin_ai.tools.account_tools  # register tools
import autocoin_ai.tools.market_tools
import autocoin_ai.tools.policy_tools

from autocoin_ai.constants import HOLD_INPUT_AMBIGUOUS, LIFECYCLE_HOLD, LIFECYCLE_READY_FOR_BE
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

EVAL_AMBIGUOUS_RESP = {
    "summary": "입력이 모호하여 홀드.",
    "user_message": "입력 내용이 모호하여 처리할 수 없습니다. 종목, 수량, 방향을 명확하게 입력해주세요.",
    "reason_codes": ["INPUT_AMBIGUOUS"],
    "schema_warnings": [],
}


def _run(example_file: str) -> dict:
    state = json.loads((EXAMPLES / example_file).read_text())
    return ensure_state_shape(state)


def test_e2e_livermore_buy():
    state = _run("livermore_buy.json")
    strategy_resp = {
        "action": "BUY",
        "size_usd": "100",
        "conviction": 0.75,
        "rationale": "추세 확인 후 진입 원칙에 부합.",
        "matched_principle_titles": [],
    }
    graph = build_agentic_order_graph()
    with patch("autocoin_ai.nodes.strategy.gemini_generate", return_value=strategy_resp), \
         patch("autocoin_ai.nodes.risk_agent.gemini_step_with_tools", return_value=_NOOP_STEP), \
         patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=EVAL_RESP):
        result = graph.invoke(state, config={"configurable": {"thread_id": state["run_id"]}})

    assert result["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert result["trader_id"] == "livermore"
    assert result["evaluator_review"]["user_message"] is not None


def test_e2e_ambiguous():
    state = _run("ambiguous_input.json")
    # intake LLM returns high ambiguity_score → HOLD_INPUT_AMBIGUOUS
    intake_resp = {
        "symbol": "",
        "side": "BUY",
        "type": "MARKET",
        "size_usd": "0",
        "trader_id": "wonyotti",
        "inferred_persona": "MODERATE",
        "persona_override_reason": None,
        "ambiguity_score": 0.9,
    }
    graph = build_agentic_order_graph()
    with patch("autocoin_ai.nodes.intake.gemini_generate", return_value=intake_resp), \
         patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=EVAL_AMBIGUOUS_RESP):
        result = graph.invoke(state, config={"configurable": {"thread_id": state["run_id"]}})

    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_INPUT_AMBIGUOUS
    assert result["evaluator_review"]["user_message"] is not None
