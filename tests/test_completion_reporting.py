from __future__ import annotations

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.constants import LIFECYCLE_BE_REJECTED, LIFECYCLE_FAILED, LIFECYCLE_REPORT_READY
from tests.fixtures import allowed_request, be_rejection_evidence, execution_result


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
