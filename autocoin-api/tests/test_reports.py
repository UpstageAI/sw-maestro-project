from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.db.crud import save_or_update_report
from app.db.models import AgentRunCheckpoint
from app.database import create_tables


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
    _ = save_or_update_report(
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


def test_create_tables_upgrades_legacy_reports_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "legacy_reports.db"
    temp_engine = create_engine(f"sqlite:///{db_path.as_posix()}")

    with temp_engine.begin() as connection:
        _ = connection.execute(
            text(
                """
                CREATE TABLE reports (
                    report_id VARCHAR PRIMARY KEY NOT NULL,
                    order_id VARCHAR,
                    report_json JSON NOT NULL,
                    created_at DATETIME
                )
                """
            )
        )

    monkeypatch.setattr("app.database.engine", temp_engine)
    create_tables()

    report_columns = {column["name"] for column in inspect(temp_engine).get_columns("reports")}
    assert "run_id" in report_columns

    temp_session = sessionmaker(autocommit=False, autoflush=False, bind=temp_engine)()
    try:
        first_report = save_or_update_report(
            temp_session,
            run_id="legacy_run_001",
            report_json={"lifecycle_status": "REPORT_READY", "user_summary": "first"},
        )
        second_report = save_or_update_report(
            temp_session,
            run_id="legacy_run_001",
            report_json={"lifecycle_status": "REPORT_READY", "user_summary": "second"},
        )

        assert first_report.report_id == second_report.report_id
        assert second_report.report_json["user_summary"] == "second"
    finally:
        temp_session.close()
        temp_engine.dispose()
