from __future__ import annotations

import pytest

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_HOLD, LIFECYCLE_READY_FOR_BE
from tests.fixtures import allowed_request, request_with_user_input


def test_same_run_resume_preserves_immutable_context_and_adds_history():
    app = AutocoinAgentApp()
    initial = app.start(request_with_user_input(market_snapshot_fresh=False))
    original_request = initial["request_context"]["request_id"]
    original_request_context = initial["request_context"]
    original_risk_trace = initial["decision_trace"]["risk"]
    original_checks = list(initial["verification_checks"])
    original_check_count = len(initial["verification_checks"])
    assert initial["lifecycle_status"] == LIFECYCLE_HOLD

    result = app.resume(
        "airun_test_001",
        {"supplemental_user_input": {"market_snapshot_fresh": True}},
        "MARKET_DATA_SUPPLIED",
    )

    assert result["run_id"] == "airun_test_001"
    assert result["request_context"]["request_id"] == original_request
    assert result["request_context"] == original_request_context
    assert result["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert result["resume_history"][0]["resume_reason"] == "MARKET_DATA_SUPPLIED"
    assert result["decision_trace_history"][0]["decision_trace"]["risk"] == original_risk_trace
    assert result["decision_trace_history"][0]["verification_checks_count"] == original_check_count
    assert result["decision_trace"]["risk"]["final_action"] == "PASS"
    assert len(result["verification_checks"]) > original_check_count
    assert result["verification_checks"][:original_check_count] == original_checks


def test_failed_run_cannot_resume_with_same_run_id():
    app = AutocoinAgentApp()
    payload = allowed_request()
    del payload["request_context"]["user_input"]["symbol"]
    result = app.start(payload)
    assert result["lifecycle_status"] == LIFECYCLE_FAILED

    with pytest.raises(ValueError):
        app.resume("airun_test_001", {"supplemental_user_input": {"symbol": "BTCUSDT"}}, "FIX_SCHEMA")
