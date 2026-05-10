from datetime import datetime, timedelta, timezone
from typing import cast
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.crud import save_or_update_report
from app.db.crud import save_or_update_checkpoint
from app.db.models import Report


_HOLD_STATE = {
    "run_id": "run_hold_001",
    "lifecycle_status": "HOLD",
    "hold_reason": "HOLD_REVIEW_REQUIRED",
    "request_context": {
        "request_id": "run_hold_001",
        "request_type": "PLACE_ORDER_TEST",
        "requested_at": "2026-01-01T00:00:00+00:00",
        "user_input": {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": "0.001",
            "price": "80000.00",
            "timeInForce": "GTC",
        },
    },
    "decision_trace": {
        "policy": {"reason_codes": [], "evidence_refs": [], "final_action": "PASS"},
        "risk": {"reason_codes": ["HOLD_REVIEW_REQUIRED"], "evidence_refs": [], "final_action": "HOLD"},
        "evaluator": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
        "execution": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
        "run_summary": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
    },
    "verification_checks": [],
    "report": {},
}

_RESUME_BODY = {
    "runId": "run_hold_001",
    "resumeReason": "USER_APPROVED_ORDER",
    "patchFields": {"approval": {"approved": True}},
}

_AI_READY = {
    **_HOLD_STATE,
    "lifecycle_status": "READY_FOR_BE",
    "hold_reason": None,
}

_BINANCE_RESP = {
    "orderId": 999,
    "symbol": "BTCUSDT",
    "status": "NEW",
    "type": "LIMIT",
    "side": "BUY",
    "clientOrderId": "test",
}


def _create_hold_checkpoint(db: Session, run_id: str = "run_hold_001", expired: bool = False):
    ttl = -1 if expired else 60
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl)
    from app.db.models import AgentRunCheckpoint
    cp = AgentRunCheckpoint(
        run_id=run_id,
        lifecycle_status="HOLD",
        hold_reason="HOLD_REVIEW_REQUIRED",
        state_json={**_HOLD_STATE, "run_id": run_id},
        schema_version="1.0",
        expires_at=expires_at,
    )
    db.add(cp)
    db.commit()


def test_resume_hold_to_ready_for_be(client: TestClient, db_session: Session):
    _create_hold_checkpoint(db_session)
    save_or_update_report(
        db_session,
        run_id="run_hold_001",
        report_json={
            "lifecycle_status": "HOLD",
            "hold_reason": "HOLD_REVIEW_REQUIRED",
            "reason_codes": ["HOLD_REVIEW_REQUIRED"],
            "user_summary": "awaiting approval",
            "decision_trace": {
                "risk": {
                    "reason_codes": ["HOLD_REVIEW_REQUIRED"],
                    "evidence_refs": [],
                    "final_action": "HOLD",
                    "notes": None,
                }
            },
            "order": None,
        },
    )
    body = {
        **_RESUME_BODY,
        "patchFields": {
            "approval": {"approved": True},
            "supplemental_user_input": {"price": "79000.00"},
        },
    }

    with patch("app.services.order_service.ai_gateway_service.resume_run", new_callable=AsyncMock) as mock_resume, \
         patch("app.services.order_service._revalidate", new_callable=AsyncMock) as mock_rv, \
         patch("app.services.order_service._submit_to_binance", new_callable=AsyncMock) as mock_submit, \
         patch("app.services.order_service.ai_gateway_service.send_completion", new_callable=AsyncMock) as mock_complete:

        mock_resume.return_value = _AI_READY
        mock_rv.return_value = None
        mock_submit.return_value = _BINANCE_RESP
        mock_complete.return_value = {**_AI_READY, "lifecycle_status": "REPORT_READY", "report": {"message": "done"}}

        resp = client.post("/api/v1/testnet/orders/resume", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "REPORT_READY"
    assert data["orderId"] == 999
    revalidated_request = mock_rv.await_args_list[0].args[0]
    submitted_request = mock_submit.await_args_list[0].args[0]
    assert revalidated_request.price == "79000.00"
    assert submitted_request.price == "79000.00"

    reports = db_session.scalars(select(Report).where(Report.run_id == "run_hold_001")).all()
    assert len(reports) == 1
    report_json = cast(dict[str, object], reports[0].report_json)
    order_json = cast(dict[str, object], report_json["order"])
    assert report_json["lifecycle_status"] == "REPORT_READY"
    assert order_json["order_id"] == 999
    assert report_json["user_summary"] == "done"


def test_resume_hold_stays_hold(client: TestClient, db_session: Session):
    _create_hold_checkpoint(db_session, run_id="run_hold_002")

    ai_still_hold = {**_HOLD_STATE, "run_id": "run_hold_002", "hold_reason": "HOLD_DATA_INSUFFICIENT"}
    body = {**_RESUME_BODY, "runId": "run_hold_002", "resumeReason": "USER_PROVIDED_DATA"}
    with patch("app.services.order_service.ai_gateway_service.resume_run", new_callable=AsyncMock) as mock_resume:
        mock_resume.return_value = ai_still_hold
        resp = client.post("/api/v1/testnet/orders/resume", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "HOLD"
    assert data["holdReason"] == "HOLD_DATA_INSUFFICIENT"


def test_resume_unknown_run_id_returns_404(client: TestClient):
    body = {**_RESUME_BODY, "runId": "nonexistent_run"}
    resp = client.post("/api/v1/testnet/orders/resume", json=body)
    assert resp.status_code == 404


def test_resume_non_hold_run_returns_400(client: TestClient, db_session: Session):
    save_or_update_checkpoint(db_session, "run_ready_001", "READY_FOR_BE", None, {})
    body = {**_RESUME_BODY, "runId": "run_ready_001"}
    resp = client.post("/api/v1/testnet/orders/resume", json=body)
    assert resp.status_code == 400


def test_resume_expired_checkpoint_returns_410(client: TestClient, db_session: Session):
    _create_hold_checkpoint(db_session, run_id="run_expired_001", expired=True)
    body = {**_RESUME_BODY, "runId": "run_expired_001"}
    resp = client.post("/api/v1/testnet/orders/resume", json=body)
    assert resp.status_code == 410
