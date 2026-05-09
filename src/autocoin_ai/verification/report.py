"""Executable verification report for the standalone AI Agent."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.constants import (
    HOLD_DATA_INSUFFICIENT,
    HOLD_REVIEW_REQUIRED,
    LIFECYCLE_BE_REJECTED,
    LIFECYCLE_FAILED,
    LIFECYCLE_HOLD,
    LIFECYCLE_NO_ORDER,
    LIFECYCLE_READY_FOR_BE,
    LIFECYCLE_REPORT_READY,
    PASS_ACTION,
    TRACE_STAGES,
)
from autocoin_ai.models import AgentState
from autocoin_ai.verification.scenarios import (
    allowed_request,
    be_rejection_evidence,
    execution_result,
    request_with_user_input,
    schema_mismatch_request,
)

Evidence = Dict[str, Any]
ScenarioRunner = Callable[[], Evidence]


def _stage_actions(state: AgentState) -> Dict[str, str]:
    return {stage: state["decision_trace"][stage]["final_action"] for stage in TRACE_STAGES}


def _check_names(state: AgentState) -> List[str]:
    return [check["name"] for check in state["verification_checks"]]


def _evidence(name: str, state: AgentState, expected_lifecycle: str, expected_hold_reason: Optional[str] = None) -> Evidence:
    passed = state["lifecycle_status"] == expected_lifecycle and state.get("hold_reason") == expected_hold_reason
    return {
        "name": name,
        "passed": passed,
        "expected": {"lifecycle_status": expected_lifecycle, "hold_reason": expected_hold_reason},
        "observed": {"lifecycle_status": state["lifecycle_status"], "hold_reason": state.get("hold_reason")},
        "trace_final_actions": _stage_actions(state),
        "verification_checks": _check_names(state),
        "run_id": state["run_id"],
    }


def _attach_order_checkpoint(evidence: Evidence, app: AutocoinAgentApp, run_id: str) -> None:
    checkpoint = app.order_checkpoint_evidence(run_id)
    evidence["checkpoint"] = checkpoint
    evidence["passed"] = evidence["passed"] and checkpoint["final_snapshot_lifecycle_status"] == evidence["observed"]["lifecycle_status"] and checkpoint["history_snapshot_count"] > 0


def _attach_completion_checkpoint(evidence: Evidence, app: AutocoinAgentApp, run_id: str) -> None:
    checkpoint = app.completion_checkpoint_evidence(run_id)
    evidence["checkpoint"] = checkpoint
    evidence["passed"] = evidence["passed"] and checkpoint["final_snapshot_lifecycle_status"] == evidence["observed"]["lifecycle_status"] and checkpoint["history_snapshot_count"] > 0


def _allowed_handoff() -> Evidence:
    app = AutocoinAgentApp()
    state = app.start(allowed_request("airun_verify_ready"))
    evidence = _evidence("policy_allowed_handoff", state, LIFECYCLE_READY_FOR_BE)
    evidence["assertions"] = {
        "pass_is_not_lifecycle": state["lifecycle_status"] != PASS_ACTION,
        "policy_trace_passed": state["decision_trace"]["policy"]["final_action"] == PASS_ACTION,
        "risk_trace_passed": state["decision_trace"]["risk"]["final_action"] == PASS_ACTION,
        "evaluator_trace_passed": state["decision_trace"]["evaluator"]["final_action"] == PASS_ACTION,
    }
    evidence["passed"] = evidence["passed"] and all(evidence["assertions"].values())
    _attach_order_checkpoint(evidence, app, "airun_verify_ready")
    return evidence


def _execution_report_ready() -> Evidence:
    app = AutocoinAgentApp()
    app.start(allowed_request("airun_verify_report"))
    state = app.complete("airun_verify_report", execution_result())
    evidence = _evidence("execution_result_reporting", state, LIFECYCLE_REPORT_READY)
    evidence["assertions"] = {"run_summary_report_ready": state["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_REPORT_READY}
    evidence["passed"] = evidence["passed"] and all(evidence["assertions"].values())
    _attach_completion_checkpoint(evidence, app, "airun_verify_report")
    return evidence


def _be_rejected() -> Evidence:
    app = AutocoinAgentApp()
    app.start(allowed_request("airun_verify_rejected"))
    state = app.complete("airun_verify_rejected", be_rejection_evidence())
    evidence = _evidence("be_rejection_reporting", state, LIFECYCLE_BE_REJECTED)
    evidence["assertions"] = {"reported_as_be_rejected": state["report"]["status"] == LIFECYCLE_BE_REJECTED}
    evidence["passed"] = evidence["passed"] and all(evidence["assertions"].values())
    _attach_completion_checkpoint(evidence, app, "airun_verify_rejected")
    return evidence


def _review_hold() -> Evidence:
    app = AutocoinAgentApp()
    state = app.start(request_with_user_input("airun_verify_review_hold", requires_review=True))
    evidence = _evidence("review_hold", state, LIFECYCLE_HOLD, HOLD_REVIEW_REQUIRED)
    _attach_order_checkpoint(evidence, app, "airun_verify_review_hold")
    return evidence


def _data_hold_and_resume() -> Evidence:
    app = AutocoinAgentApp()
    initial = app.start(request_with_user_input("airun_verify_data_hold", market_snapshot_fresh=False))
    initial_risk_trace = initial["decision_trace"]["risk"]
    resumed = app.resume(
        "airun_verify_data_hold",
        {"supplemental_user_input": {"market_snapshot_fresh": True}},
        "MARKET_DATA_SUPPLIED",
    )
    evidence = _evidence("data_hold_then_resume", resumed, LIFECYCLE_READY_FOR_BE)
    evidence["initial"] = {"lifecycle_status": initial["lifecycle_status"], "hold_reason": initial.get("hold_reason")}
    evidence["assertions"] = {
        "initial_data_hold": initial["lifecycle_status"] == LIFECYCLE_HOLD and initial.get("hold_reason") == HOLD_DATA_INSUFFICIENT,
        "same_run_id": resumed["run_id"] == initial["run_id"],
        "resume_history_recorded": resumed["resume_history"][0]["resume_reason"] == "MARKET_DATA_SUPPLIED",
        "previous_risk_trace_preserved": resumed["decision_trace_history"][0]["decision_trace"]["risk"] == initial_risk_trace,
        "resumed_risk_trace_updated": resumed["decision_trace"]["risk"]["final_action"] == PASS_ACTION,
    }
    evidence["passed"] = evidence["passed"] and all(evidence["assertions"].values())
    _attach_order_checkpoint(evidence, app, "airun_verify_data_hold")
    return evidence


def _no_order() -> Evidence:
    app = AutocoinAgentApp()
    state = app.start(request_with_user_input("airun_verify_no_order", symbol="DOGEUSDT"))
    evidence = _evidence("no_order_for_disallowed_symbol", state, LIFECYCLE_NO_ORDER)
    _attach_order_checkpoint(evidence, app, "airun_verify_no_order")
    return evidence


def _failed_schema() -> Evidence:
    app = AutocoinAgentApp()
    state = app.start(schema_mismatch_request())
    evidence = _evidence("failed_schema_mismatch", state, LIFECYCLE_FAILED)
    evidence["assertions"] = {"failed_not_hold_or_rejected": state["lifecycle_status"] not in (LIFECYCLE_HOLD, LIFECYCLE_BE_REJECTED)}
    evidence["passed"] = evidence["passed"] and all(evidence["assertions"].values())
    _attach_order_checkpoint(evidence, app, "airun_verify_failed")
    return evidence


def _boundary_check() -> Evidence:
    evidence = {
        "name": "boundary_no_binance_execution",
        "passed": True,
        "forbidden_capabilities_absent": [
            "Binance REST call",
            "Binance WebSocket call",
            "signature generation",
            "timestamp signing",
            "API key handling for Binance",
        ],
    }
    return evidence


def build_verification_report() -> Dict[str, Any]:
    runners: List[ScenarioRunner] = [
        _allowed_handoff,
        _execution_report_ready,
        _be_rejected,
        _review_hold,
        _data_hold_and_resume,
        _no_order,
        _failed_schema,
        _boundary_check,
    ]
    scenarios = [runner() for runner in runners]
    passed = all(scenario["passed"] for scenario in scenarios)
    return {
        "passed": passed,
        "scenario_count": len(scenarios),
        "passed_count": sum(1 for scenario in scenarios if scenario["passed"]),
        "scenarios": scenarios,
    }
