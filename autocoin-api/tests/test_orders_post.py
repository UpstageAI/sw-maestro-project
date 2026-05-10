from typing import cast
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Report


_LIMIT_ORDER_BODY = {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": "0.001",
    "price": "80000.00",
    "timeInForce": "GTC",
}

_MARKET_ORDER_BODY = {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "quoteOrderQty": "10",
}

_AI_READY = {
    "run_id": "run_test001",
    "lifecycle_status": "READY_FOR_BE",
    "decision_trace": {
        "policy": {"reason_codes": ["ORDER_INTENT_NORMALIZED"], "evidence_refs": [], "final_action": "PASS"},
        "risk": {"reason_codes": ["ALL_CHECKS_PASSED"], "evidence_refs": [], "final_action": "PASS"},
        "evaluator": {"reason_codes": ["EVIDENCE_SUFFICIENT"], "evidence_refs": [], "final_action": "PASS"},
        "execution": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
        "run_summary": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
    },
    "verification_checks": [],
    "hold_reason": None,
    "report": {},
}

_AI_REPORT_READY = {
    **_AI_READY,
    "lifecycle_status": "REPORT_READY",
    "report": {"status": "REPORT_READY", "message": "done"},
}

_BINANCE_ORDER_RESP = {
    "orderId": 123456,
    "symbol": "BTCUSDT",
    "status": "NEW",
    "type": "LIMIT",
    "side": "BUY",
    "clientOrderId": "test-order",
}


def test_create_order_ready_for_be_success(client: TestClient, db_session: Session):
    with patch("app.services.order_service.ai_gateway_service.start_run", new_callable=AsyncMock) as mock_start, \
         patch("app.services.order_service._revalidate", new_callable=AsyncMock) as mock_rv, \
         patch("app.services.order_service._submit_to_binance", new_callable=AsyncMock) as mock_submit, \
         patch("app.services.order_service.ai_gateway_service.send_completion", new_callable=AsyncMock) as mock_complete:

        mock_start.return_value = _AI_READY
        mock_rv.return_value = None
        mock_submit.return_value = _BINANCE_ORDER_RESP
        mock_complete.return_value = _AI_REPORT_READY

        resp = client.post("/api/v1/testnet/orders", json=_LIMIT_ORDER_BODY)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "REPORT_READY"
    assert data["orderId"] == 123456
    assert data["symbol"] == "BTCUSDT"
    assert data["runId"] is not None

    report = db_session.scalars(select(Report).where(Report.run_id == data["runId"])).one()
    report_json = cast(dict[str, object], report.report_json)
    order_json = cast(dict[str, object], report_json["order"])
    assert report_json["lifecycle_status"] == "REPORT_READY"
    assert order_json["order_id"] == 123456
    assert report_json["user_summary"] == "done"


def test_create_order_be_rejected(client: TestClient, db_session: Session):
    with patch("app.services.order_service.ai_gateway_service.start_run", new_callable=AsyncMock) as mock_start, \
         patch("app.services.order_service._revalidate", new_callable=AsyncMock) as mock_rv, \
         patch("app.services.order_service.ai_gateway_service.send_completion", new_callable=AsyncMock) as mock_complete:

        mock_start.return_value = _AI_READY
        mock_rv.return_value = {"reason_codes": ["MIN_NOTIONAL_NOT_MET"], "notes": "blocked"}
        mock_complete.return_value = {**_AI_READY, "lifecycle_status": "BE_REJECTED", "report": {"message": "blocked"}}

        resp = client.post("/api/v1/testnet/orders", json=_LIMIT_ORDER_BODY)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "BE_REJECTED"
    assert "MIN_NOTIONAL_NOT_MET" in data["reasonCodes"]

    report = db_session.scalars(select(Report).where(Report.run_id == data["runId"])).one()
    report_json = cast(dict[str, object], report.report_json)
    assert report_json["lifecycle_status"] == "BE_REJECTED"
    assert report_json["reason_codes"] == ["MIN_NOTIONAL_NOT_MET"]
    assert report_json["user_summary"] == "blocked"


def test_create_order_hold(client: TestClient, db_session: Session):
    ai_hold = {
        **_AI_READY,
        "lifecycle_status": "HOLD",
        "hold_reason": "HOLD_REVIEW_REQUIRED",
        "evaluator_review": {"user_summary": "hold fallback summary"},
    }
    with patch("app.services.order_service.ai_gateway_service.start_run", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = ai_hold
        resp = client.post("/api/v1/testnet/orders", json=_LIMIT_ORDER_BODY)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "HOLD"
    assert data["holdReason"] == "HOLD_REVIEW_REQUIRED"
    assert data["runId"] is not None

    report = db_session.scalars(select(Report).where(Report.run_id == data["runId"])).one()
    report_json = cast(dict[str, object], report.report_json)
    assert report_json["lifecycle_status"] == "HOLD"
    assert report_json["hold_reason"] == "HOLD_REVIEW_REQUIRED"
    assert report_json["user_summary"] == "hold fallback summary"


def test_create_order_no_order(client: TestClient, db_session: Session):
    ai_no_order = {
        **_AI_READY,
        "lifecycle_status": "NO_ORDER",
        "evaluator_review": {"user_summary": "no order fallback summary"},
        "decision_trace": {
            "policy": {"reason_codes": ["ORDER_INTENT_NORMALIZED"], "evidence_refs": [], "final_action": "PASS"},
            "risk": {"reason_codes": ["RISK_THRESHOLD_EXCEEDED"], "evidence_refs": [], "final_action": "NO_ORDER"},
            "evaluator": {"reason_codes": ["EVIDENCE_SUFFICIENT"], "evidence_refs": [], "final_action": "PASS"},
            "execution": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
            "run_summary": {"reason_codes": [], "evidence_refs": [], "final_action": ""},
        },
    }
    with patch("app.services.order_service.ai_gateway_service.start_run", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = ai_no_order
        resp = client.post("/api/v1/testnet/orders", json=_LIMIT_ORDER_BODY)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "NO_ORDER"
    assert "RISK_THRESHOLD_EXCEEDED" in data["reasonCodes"]

    report = db_session.scalars(select(Report).where(Report.run_id == data["runId"])).one()
    report_json = cast(dict[str, object], report.report_json)
    assert report_json["lifecycle_status"] == "NO_ORDER"
    assert report_json["reason_codes"] == ["RISK_THRESHOLD_EXCEEDED"]
    assert report_json["user_summary"] == "no order fallback summary"


def test_create_order_ai_unavailable(client: TestClient):
    from app.main import app
    from fastapi.testclient import TestClient as TC
    with patch("app.services.order_service.ai_gateway_service.start_run", new_callable=AsyncMock) as mock_start:
        mock_start.side_effect = Exception("Connection refused")
        with TC(app, raise_server_exceptions=False) as c:
            resp = c.post("/api/v1/testnet/orders", json=_LIMIT_ORDER_BODY)

    assert resp.status_code == 500


def test_create_order_validation_error_missing_price(client: TestClient):
    body = {"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "quantity": "0.001"}
    resp = client.post("/api/v1/testnet/orders", json=body)
    assert resp.status_code == 422


def test_create_order_response_camel_case(client: TestClient):
    with patch("app.services.order_service.ai_gateway_service.start_run", new_callable=AsyncMock) as mock_start, \
         patch("app.services.order_service._revalidate", new_callable=AsyncMock) as mock_rv, \
         patch("app.services.order_service._submit_to_binance", new_callable=AsyncMock) as mock_submit, \
         patch("app.services.order_service.ai_gateway_service.send_completion", new_callable=AsyncMock) as mock_complete:

        mock_start.return_value = _AI_READY
        mock_rv.return_value = None
        mock_submit.return_value = _BINANCE_ORDER_RESP
        mock_complete.return_value = _AI_REPORT_READY

        resp = client.post("/api/v1/testnet/orders", json=_LIMIT_ORDER_BODY)

    data = resp.json()
    assert "runId" in data
    assert "lifecycleStatus" in data
    assert "run_id" not in data
    assert "lifecycle_status" not in data
