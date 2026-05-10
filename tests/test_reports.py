from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.crud import save_or_update_report
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


def _create_published_report(
    db: Session,
    run_id: str = "run_report_001",
    lifecycle_status: str = "REPORT_READY",
):
    save_or_update_report(
        db,
        run_id=run_id,
        report_json={
            "lifecycle_status": lifecycle_status,
            "hold_reason": None,
            "reason_codes": ["ORDER_RESPONSE_VERIFIED"],
            "user_summary": "done",
            "decision_trace": {
                "execution": {
                    "reason_codes": ["ORDER_RESPONSE_VERIFIED"],
                    "evidence_refs": ["execution_result.orderId"],
                    "final_action": lifecycle_status,
                    "notes": None,
                }
            },
            "order": {
                "order_id": 123456,
                "symbol": "BTCUSDT",
                "status": "NEW",
                "type": "LIMIT",
                "side": "BUY",
                "client_order_id": "test-order",
            },
        },
    )


def test_get_run_report_success(client: TestClient, db_session: Session):
    _create_published_report(db_session)

    resp = client.get("/api/v1/testnet/orders/report?runId=run_report_001")

    assert resp.status_code == 200
    data = resp.json()
    assert data["runId"] == "run_report_001"
    assert data["report"]["lifecycleStatus"] == "REPORT_READY"
    assert data["report"]["userSummary"] == "done"
    assert data["report"]["order"]["orderId"] == 123456


def test_get_run_report_prefers_persisted_report_over_checkpoint(client: TestClient, db_session: Session):
    _create_report_checkpoint(db_session, report={"status": "checkpoint-only", "message": "stale"})
    _create_published_report(db_session, run_id="run_report_001")

    resp = client.get("/api/v1/testnet/orders/report?runId=run_report_001")

    assert resp.status_code == 200
    data = resp.json()
    assert data["report"]["userSummary"] == "done"
    assert data["report"]["lifecycleStatus"] == "REPORT_READY"


def test_get_run_report_missing_run_returns_404(client: TestClient):
    resp = client.get("/api/v1/testnet/orders/report?runId=missing_run")

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "REQUEST_FAILED"


def test_get_run_report_missing_report_returns_404(client: TestClient, db_session: Session):
    _create_report_checkpoint(db_session, run_id="run_report_empty", report={})

    resp = client.get("/api/v1/testnet/orders/report?runId=run_report_empty")

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "REQUEST_FAILED"
