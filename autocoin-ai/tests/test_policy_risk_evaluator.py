from __future__ import annotations

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.constants import (
    HOLD_DATA_INSUFFICIENT,
    HOLD_REVIEW_REQUIRED,
    LIFECYCLE_HOLD,
    LIFECYCLE_NO_ORDER,
)
from tests.fixtures import request_with_user_input


def test_review_hold_is_separated_from_data_hold():
    result = AutocoinAgentApp().start(request_with_user_input(requires_review=True))

    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_REVIEW_REQUIRED
    assert result["decision_trace"]["risk"]["reason_codes"] == ["HUMAN_REVIEW_REQUIRED"]
    assert result["evaluator_review"]["reason_codes"]
    assert result["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_HOLD


def test_data_hold_is_used_for_stale_market_snapshot():
    result = AutocoinAgentApp().start(request_with_user_input(market_snapshot_fresh=False))

    assert result["lifecycle_status"] == LIFECYCLE_HOLD
    assert result["hold_reason"] == HOLD_DATA_INSUFFICIENT
    assert result["decision_trace"]["risk"]["reason_codes"] == ["STALE_MARKET_SNAPSHOT"]
    assert result["evaluator_review"]["summary"]
    assert result["risk_assessment"]["verdict"] == LIFECYCLE_HOLD


def test_forbidden_or_unknown_symbol_returns_no_order():
    result = AutocoinAgentApp().start(request_with_user_input(symbol="DOGEUSDT"))

    assert result["lifecycle_status"] == LIFECYCLE_NO_ORDER
    assert result["hold_reason"] is None
    assert result["decision_trace"]["risk"]["reason_codes"] == ["SYMBOL_NOT_ALLOWED"]
    assert result["evaluator_review"]["user_message"]
    assert result["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_NO_ORDER
