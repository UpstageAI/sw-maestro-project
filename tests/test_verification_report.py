from __future__ import annotations

from autocoin_ai.verification import build_verification_report


def test_verification_report_covers_all_contract_scenarios():
    report = build_verification_report()

    assert report["passed"] is True
    assert report["scenario_count"] == 8
    assert report["passed_count"] == 8
    names = {scenario["name"] for scenario in report["scenarios"]}
    assert names == {
        "policy_allowed_handoff",
        "execution_result_reporting",
        "be_rejection_reporting",
        "review_hold",
        "data_hold_then_resume",
        "no_order_for_disallowed_symbol",
        "failed_schema_mismatch",
        "boundary_no_binance_execution",
    }
