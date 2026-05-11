from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.db.crud import save_or_update_report
from app.services.report_service import save_run_report
from app.db.models import AgentRunCheckpoint, Report
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


def _create_trace_checkpoint(
    db: Session,
    run_id: str = "run_cadence_001",
    lifecycle_status: str = "REPORT_READY",
):
    checkpoint = AgentRunCheckpoint(
        run_id=run_id,
        lifecycle_status=lifecycle_status,
        hold_reason=None,
        state_json={
            "run_id": run_id,
            "lifecycle_status": lifecycle_status,
            "decision_trace": {
                "policy": {"reason_codes": ["ORDER_INTENT_NORMALIZED"], "evidence_refs": [], "final_action": "PASS"},
                "risk": {"reason_codes": ["ALL_CHECKS_PASSED"], "evidence_refs": [], "final_action": "PASS"},
                "evaluator": {"reason_codes": ["EVIDENCE_SUFFICIENT"], "evidence_refs": [], "final_action": "PASS"},
                "execution": {"reason_codes": ["ORDER_RESPONSE_VERIFIED"], "evidence_refs": [], "final_action": "REPORT_READY"},
                "run_summary": {"reason_codes": ["ORDER_RESPONSE_VERIFIED"], "evidence_refs": [], "final_action": "REPORT_READY"},
            },
        },
        schema_version="1.0",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    db.add(checkpoint)
    db.commit()
    db.refresh(checkpoint)
    return checkpoint


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


def test_get_run_report_cadence_success(client: TestClient, db_session: Session):
    checkpoint = _create_trace_checkpoint(db_session)
    _create_published_report(db_session, run_id="run_cadence_001")
    report = db_session.query(Report).filter(Report.run_id == "run_cadence_001").one()
    report.created_at = checkpoint.created_at + timedelta(seconds=1)
    db_session.commit()

    resp = client.get("/api/v1/testnet/orders/report/cadence?runId=run_cadence_001")

    assert resp.status_code == 200
    data = resp.json()
    assert data["runId"] == "run_cadence_001"
    assert [event["eventType"] for event in data["events"]] == [
        "request_accepted",
        "policy_retrieval_complete",
        "policy_complete",
        "risk_gate_complete",
        "evaluator_complete",
        "be_revalidation_complete",
        "final_report_ready",
    ]
    assert data["events"][-1]["lifecycleStatus"] == "REPORT_READY"


def test_get_run_report_cadence_checkpoint_only_run(client: TestClient, db_session: Session):
    _create_trace_checkpoint(db_session, run_id="run_hold_cadence_001", lifecycle_status="HOLD")

    resp = client.get("/api/v1/testnet/orders/report/cadence?runId=run_hold_cadence_001")

    assert resp.status_code == 200
    data = resp.json()
    assert data["runId"] == "run_hold_cadence_001"
    assert data["events"][-1]["eventType"] == "be_revalidation_complete"
    assert all(event["eventType"] != "final_report_ready" for event in data["events"])


def test_get_run_report_cadence_missing_run_returns_404(client: TestClient):
    resp = client.get("/api/v1/testnet/orders/report/cadence?runId=missing_run")

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "REQUEST_FAILED"


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


def test_get_run_report_uses_non_risk_reason_codes_for_hold(client: TestClient, db_session: Session):
    save_run_report(
        db_session,
        run_id="run_hold_policy_001",
        ai_state={
            "run_id": "run_hold_policy_001",
            "lifecycle_status": "HOLD",
            "hold_reason": "HOLD_REVIEW_REQUIRED",
            "decision_trace": {
                "policy": {
                    "reason_codes": ["INPUT_REQUIRES_CONFIRMATION"],
                    "evidence_refs": ["request_context.user_input"],
                    "final_action": "HOLD",
                    "notes": "confirmation required",
                },
                "risk": {
                    "reason_codes": [],
                    "evidence_refs": [],
                    "final_action": "",
                    "notes": None,
                },
            },
            "evaluator_review": {"user_summary": "awaiting confirmation"},
        },
    )

    resp = client.get("/api/v1/testnet/orders/report?runId=run_hold_policy_001")

    assert resp.status_code == 200
    data = resp.json()
    assert data["report"]["lifecycleStatus"] == "HOLD"
    assert data["report"]["reasonCodes"] == ["INPUT_REQUIRES_CONFIRMATION"]
    assert data["report"]["userSummary"] == "awaiting confirmation"


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
