from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.crud import get_checkpoint, save_report
from app.db.models import Report
from app.models.responses import RunReportResponse


def save_run_report(db: Session, report_json: dict[str, Any], order_id: str | None = None) -> Report:
    return save_report(db, report_json=report_json, order_id=order_id)


def get_run_report(db: Session, run_id: str) -> RunReportResponse:
    checkpoint = get_checkpoint(db, run_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    report = checkpoint.state_json.get("report")
    if not report:
        raise HTTPException(status_code=404, detail=f"report not found for run_id: {run_id}")

    return RunReportResponse(run_id=run_id, report=cast(dict[str, Any], report))
