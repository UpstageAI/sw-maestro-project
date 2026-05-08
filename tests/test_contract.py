from __future__ import annotations

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_READY_FOR_BE, PASS_ACTION, TRACE_STAGES
from tests.fixtures import allowed_request


def test_allowed_request_reaches_ready_for_be_with_canonical_trace():
    result = AutocoinAgentApp().start(allowed_request())

    assert result["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert result["decision_trace"]["policy"]["final_action"] == PASS_ACTION
    assert result["decision_trace"]["risk"]["final_action"] == PASS_ACTION
    assert result["decision_trace"]["evaluator"]["final_action"] == PASS_ACTION
    assert result["lifecycle_status"] != PASS_ACTION
    assert set(TRACE_STAGES).issubset(result["decision_trace"].keys())
    assert result["policy_context"]["policy_refs"] == ["policy.symbol_allowlist", "policy.spot_testnet_only"]


def test_schema_mismatch_becomes_failed_not_hold_or_rejected():
    payload = allowed_request()
    del payload["request_context"]["user_input"]["symbol"]

    result = AutocoinAgentApp().start(payload)

    assert result["lifecycle_status"] == LIFECYCLE_FAILED
    assert result["decision_trace"]["policy"]["final_action"] == LIFECYCLE_FAILED
    assert result["verification_checks"][0]["result"] == "fail"
