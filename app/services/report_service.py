from typing import Literal, cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.crud import get_checkpoint, get_report_by_run_id, save_or_update_report
from app.db.models import Report
from app.models.responses import (
    DecisionTraceResponse,
    DecisionTraceStageResponse,
    PublishedOrderOutcome,
    PublishedRunReport,
    RunReportResponse,
)

JsonDict = dict[str, object]
OrderStatusValue = Literal["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]


def _as_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_order_status(value: object) -> OrderStatusValue | None:
    status = _as_string(value)
    if status in {"NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"}:
        return cast(OrderStatusValue, status)
    return None


def _build_decision_trace(ai_state: JsonDict) -> DecisionTraceResponse | None:
    raw_trace = ai_state.get("decision_trace")
    if not isinstance(raw_trace, dict):
        return None
    trace_dict = cast(JsonDict, raw_trace)

    def _stage(name: str) -> DecisionTraceStageResponse | None:
        raw_stage = trace_dict.get(name)
        if not isinstance(raw_stage, dict):
            return None
        stage_dict = cast(JsonDict, raw_stage)
        return DecisionTraceStageResponse(
            reason_codes=_as_string_list(stage_dict.get("reason_codes")),
            evidence_refs=_as_string_list(stage_dict.get("evidence_refs")),
            final_action=_as_string(stage_dict.get("final_action")),
            notes=_as_string(stage_dict.get("notes")),
        )

    return DecisionTraceResponse(
        policy=_stage("policy"),
        risk=_stage("risk"),
        evaluator=_stage("evaluator"),
        execution=_stage("execution"),
        run_summary=_stage("run_summary"),
    )


def _extract_reason_codes(ai_state: JsonDict, lifecycle_status: str, fallback_reason_codes: list[str] | None) -> list[str]:
    if fallback_reason_codes:
        return fallback_reason_codes

    trace = _build_decision_trace(ai_state)
    if lifecycle_status in {"HOLD", "NO_ORDER"}:
        stage = trace.risk if trace else None
        return stage.reason_codes if stage else []
    if lifecycle_status in {"BE_REJECTED", "REPORT_READY"}:
        if trace and trace.execution and trace.execution.reason_codes:
            return trace.execution.reason_codes
        if trace and trace.run_summary and trace.run_summary.reason_codes:
            return trace.run_summary.reason_codes
    return []


def _build_order_outcome(order_outcome: JsonDict | None) -> PublishedOrderOutcome | None:
    if not isinstance(order_outcome, dict) or not order_outcome:
        return None

    return PublishedOrderOutcome(
        order_id=_as_int(order_outcome.get("orderId")),
        symbol=_as_string(order_outcome.get("symbol")),
        status=_as_order_status(order_outcome.get("status")),
        type=_as_string(order_outcome.get("type")),
        side=_as_string(order_outcome.get("side")),
    )


def _extract_evaluator_review_summary(ai_state: JsonDict) -> str | None:
    raw_review = ai_state.get("evaluator_review")
    if isinstance(raw_review, str):
        return raw_review
    if not isinstance(raw_review, dict):
        return None

    review_dict = cast(JsonDict, raw_review)
    for key in ("user_summary", "summary", "message", "notes", "content"):
        summary = _as_string(review_dict.get(key))
        if summary:
            return summary
    return None


def build_published_run_report(
    ai_state: JsonDict,
    order_outcome: JsonDict | None = None,
    fallback_reason_codes: list[str] | None = None,
) -> PublishedRunReport:
    lifecycle_status = _as_string(ai_state.get("lifecycle_status")) or "FAILED"
    raw_report = ai_state.get("report")
    ai_report = cast(JsonDict, raw_report) if isinstance(raw_report, dict) else None

    return PublishedRunReport(
        lifecycle_status=lifecycle_status,
        hold_reason=_as_string(ai_state.get("hold_reason")),
        reason_codes=_extract_reason_codes(ai_state, lifecycle_status, fallback_reason_codes),
        user_summary=(_as_string(ai_report.get("user_summary")) if ai_report else None)
        or (_as_string(ai_report.get("message")) if ai_report else None)
        or (
            _extract_evaluator_review_summary(ai_state)
            if lifecycle_status in {"HOLD", "NO_ORDER"}
            else None
        ),
        decision_trace=_build_decision_trace(ai_state),
        order=_build_order_outcome(order_outcome),
    )


def save_run_report(
    db: Session,
    run_id: str,
    ai_state: JsonDict,
    order_id: str | None = None,
    order_outcome: JsonDict | None = None,
    fallback_reason_codes: list[str] | None = None,
) -> Report:
    published_report = build_published_run_report(ai_state, order_outcome, fallback_reason_codes)
    return save_or_update_report(
        db,
        run_id=run_id,
        report_json=published_report.model_dump(),
        order_id=order_id,
    )


def get_run_report(db: Session, run_id: str) -> RunReportResponse:
    report = get_report_by_run_id(db, run_id)
    if report:
        return RunReportResponse(
            run_id=run_id,
            report=PublishedRunReport.model_validate(report.report_json),
        )

    checkpoint = get_checkpoint(db, run_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    raise HTTPException(status_code=404, detail=f"report not found for run_id: {run_id}")
