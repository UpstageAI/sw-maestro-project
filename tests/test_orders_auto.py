from typing import cast
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Report


_AUTO_ORDER_BODY = {
    "rawText": "BTC를 50 USDT만큼 공격적으로 매수해줘",
}

_AI_AGENTIC_READY = {
    "run_id": "run_agentic001",
    "lifecycle_status": "READY_FOR_BE",
    "normalized_order_intent": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": "50",
    },
    "trader_id": "wonyotti",
    "inferred_persona": "AGGRESSIVE",
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

_AI_AGENTIC_REPORT_READY = {
    **_AI_AGENTIC_READY,
    "lifecycle_status": "REPORT_READY",
    "report": {"status": "REPORT_READY", "message": "done"},
}

_BINANCE_ORDER_RESP = {
    "orderId": 555001,
    "symbol": "BTCUSDT",
    "status": "NEW",
    "type": "MARKET",
    "side": "BUY",
    "clientOrderId": "agentic-order",
}


def test_create_auto_order_ready_for_be_success(client: TestClient, db_session: Session):
    with patch("app.services.order_service.ai_gateway_service.start_agentic_run", new_callable=AsyncMock) as mock_start, \
         patch("app.services.order_service._revalidate", new_callable=AsyncMock) as mock_rv, \
         patch("app.services.order_service._submit_to_binance", new_callable=AsyncMock) as mock_submit, \
         patch("app.services.order_service.ai_gateway_service.send_completion", new_callable=AsyncMock) as mock_complete:

        mock_start.return_value = _AI_AGENTIC_READY
        mock_rv.return_value = None
        mock_submit.return_value = _BINANCE_ORDER_RESP
        mock_complete.return_value = _AI_AGENTIC_REPORT_READY

        resp = client.post("/api/v1/testnet/orders/auto", json=_AUTO_ORDER_BODY)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "REPORT_READY"
    assert data["normalizedOrderIntent"]["symbol"] == "BTCUSDT"
    assert data["normalizedOrderIntent"]["quoteOrderQty"] == "50"
    assert data["traderId"] == "wonyotti"
    assert data["inferredPersona"] == "AGGRESSIVE"
    revalidated_request = mock_rv.await_args_list[0].args[0]
    assert revalidated_request.quote_order_qty == "50"

    report = db_session.scalars(select(Report).where(Report.run_id == data["runId"])).one()
    report_json = cast(dict[str, object], report.report_json)
    assert report_json["lifecycle_status"] == "REPORT_READY"


def test_create_auto_order_hold_returns_non_resumable_state(client: TestClient):
    ai_hold = {
        **_AI_AGENTIC_READY,
        "lifecycle_status": "HOLD",
        "hold_reason": "HOLD_INPUT_AMBIGUOUS",
        "decision_trace": {
            **cast(dict[str, object], _AI_AGENTIC_READY["decision_trace"]),
            "policy": {"reason_codes": ["INPUT_AMBIGUOUS"], "evidence_refs": [], "final_action": "HOLD"},
        },
    }
    with patch("app.services.order_service.ai_gateway_service.start_agentic_run", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = ai_hold
        resp = client.post("/api/v1/testnet/orders/auto", json=_AUTO_ORDER_BODY)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "HOLD"
    assert data["holdReason"] == "HOLD_INPUT_AMBIGUOUS"
    assert data["normalizedOrderIntent"]["symbol"] == "BTCUSDT"


def test_create_auto_order_invalid_normalized_intent_be_rejected(client: TestClient):
    ai_invalid = {
        **_AI_AGENTIC_READY,
        "normalized_order_intent": {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
        },
    }
    ai_rejected = {
        **ai_invalid,
        "lifecycle_status": "BE_REJECTED",
        "report": {"message": "blocked"},
    }
    with patch("app.services.order_service.ai_gateway_service.start_agentic_run", new_callable=AsyncMock) as mock_start, \
         patch("app.services.order_service.ai_gateway_service.send_completion", new_callable=AsyncMock) as mock_complete:
        mock_start.return_value = ai_invalid
        mock_complete.return_value = ai_rejected
        resp = client.post("/api/v1/testnet/orders/auto", json=_AUTO_ORDER_BODY)

    assert resp.status_code == 200
    data = resp.json()
    assert data["lifecycleStatus"] == "BE_REJECTED"
    assert data["reasonCodes"] == ["NORMALIZED_INTENT_INVALID"]


def test_create_auto_order_validation_error_missing_raw_text(client: TestClient):
    resp = client.post("/api/v1/testnet/orders/auto", json={"rawText": "   "})
    assert resp.status_code == 422
