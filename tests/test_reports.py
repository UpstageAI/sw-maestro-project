from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import AgentRunCheckpoint


def _create_report_checkpoint(
    db: Session,
    run_id: str = "run_report_001",
    report: dict[str, object] | None = None,
):
    checkpoint = AgentRunCheckpoint(
        run_id=run_id,
        lifecycle_status="REPORT_READY",
        hold_reason=None,
        state_json={
            "run_id": run_id,
            "lifecycle_status": "REPORT_READY",
            "report": report if report is not None else {"status": "success", "message": "done"},
        },
        schema_version="1.0",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    db.add(checkpoint)
    db.commit()


def test_get_run_report_success(client: TestClient, db_session: Session):
    _create_report_checkpoint(db_session)

    resp = client.get("/api/v1/testnet/orders/report?runId=run_report_001")

    assert resp.status_code == 200
    data = resp.json()
    assert data["runId"] == "run_report_001"
    assert data["report"] == {"status": "success", "message": "done"}


def test_get_run_report_missing_run_returns_404(client: TestClient):
    resp = client.get("/api/v1/testnet/orders/report?runId=missing_run")

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "REQUEST_FAILED"


def test_get_run_report_missing_report_returns_404(client: TestClient, db_session: Session):
    _create_report_checkpoint(db_session, run_id="run_report_empty", report={})

    resp = client.get("/api/v1/testnet/orders/report?runId=run_report_empty")

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "REQUEST_FAILED"
