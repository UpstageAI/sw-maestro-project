from __future__ import annotations

import pytest

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.constants import LIFECYCLE_BE_REJECTED, LIFECYCLE_FAILED, LIFECYCLE_HOLD, LIFECYCLE_REPORT_READY
from autocoin_ai.run_store import JsonFileRunStore
from tests.fixtures import allowed_request, be_rejection_evidence, execution_result, request_with_user_input


def test_execution_result_completes_report_ready():
    app = AutocoinAgentApp()
    app.start(allowed_request())

    result = app.complete("airun_test_001", execution_result())

    assert result["lifecycle_status"] == LIFECYCLE_REPORT_READY
    assert result["decision_trace"]["execution"]["final_action"] == LIFECYCLE_REPORT_READY
    assert result["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_REPORT_READY


def test_be_rejection_remains_be_rejected_not_failed():
    app = AutocoinAgentApp()
    app.start(allowed_request())

    result = app.complete("airun_test_001", be_rejection_evidence())

    assert result["lifecycle_status"] == LIFECYCLE_BE_REJECTED
    assert result["decision_trace"]["execution"]["final_action"] == LIFECYCLE_BE_REJECTED
    assert result["report"]["status"] == LIFECYCLE_BE_REJECTED


def test_invalid_completion_payload_fails_contract():
    app = AutocoinAgentApp()
    app.start(allowed_request())

    result = app.complete("airun_test_001", {})

    assert result["lifecycle_status"] == LIFECYCLE_FAILED
    assert result["decision_trace"]["execution"]["reason_codes"] == ["COMPLETION_PAYLOAD_INVALID"]


def test_hold_run_cannot_complete():
    app = AutocoinAgentApp()
    state = app.start(request_with_user_input(market_snapshot_fresh=False))

    assert state["lifecycle_status"] == LIFECYCLE_HOLD

    with pytest.raises(ValueError, match="only READY_FOR_BE runs can be completed"):
        app.complete("airun_test_001", execution_result())


def test_failed_run_cannot_complete():
    app = AutocoinAgentApp()
    payload = allowed_request()
    del payload["request_context"]["user_input"]["symbol"]
    state = app.start(payload)

    assert state["lifecycle_status"] == LIFECYCLE_FAILED

    with pytest.raises(ValueError, match="only READY_FOR_BE runs can be completed"):
        app.complete("airun_test_001", execution_result())


def test_complete_survives_app_restart_with_file_run_store(tmp_path):
    store_path = tmp_path / "runs.json"
    first_app = AutocoinAgentApp(run_store=JsonFileRunStore(store_path))
    ready = first_app.start(allowed_request())

    assert ready["lifecycle_status"] == "READY_FOR_BE"

    restarted_app = AutocoinAgentApp(run_store=JsonFileRunStore(store_path))
    completed = restarted_app.complete("airun_test_001", execution_result())

    assert completed["lifecycle_status"] == LIFECYCLE_REPORT_READY
    assert completed["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_REPORT_READY
