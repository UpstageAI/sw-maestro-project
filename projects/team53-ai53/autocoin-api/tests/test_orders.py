from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_get_order_status_by_order_id(client: TestClient):
    with patch("app.services.order_service.get_order_status", new_callable=AsyncMock) as mock:
        from app.models.responses import OrderStatusResponse
        mock.return_value = OrderStatusResponse(
            order_id=123456789,
            symbol="BTCUSDT",
            status="FILLED",
            executed_qty="0.00076900",
        )
        resp = client.get("/api/v1/testnet/orders/status?symbol=BTCUSDT&orderId=123456789")

    assert resp.status_code == 200
    data = resp.json()
    assert data["orderId"] == 123456789
    assert data["symbol"] == "BTCUSDT"
    assert data["status"] == "FILLED"
    assert data["executedQty"] == "0.00076900"


def test_get_order_status_by_client_order_id(client: TestClient):
    with patch("app.services.order_service.get_order_status", new_callable=AsyncMock) as mock:
        from app.models.responses import OrderStatusResponse
        mock.return_value = OrderStatusResponse(
            order_id=123456789,
            symbol="BTCUSDT",
            status="NEW",
            executed_qty="0.00000000",
        )
        resp = client.get(
            "/api/v1/testnet/orders/status?symbol=BTCUSDT&origClientOrderId=demo-001"
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "NEW"


def test_get_order_status_missing_symbol(client: TestClient):
    resp = client.get("/api/v1/testnet/orders/status?orderId=123")
    assert resp.status_code == 422


def test_get_order_status_missing_identifier(client: TestClient):
    resp = client.get("/api/v1/testnet/orders/status?symbol=BTCUSDT")
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_get_order_status_binance_failure():
    from app.main import app
    with patch("app.services.order_service.get_order_status", new_callable=AsyncMock) as mock:
        mock.side_effect = Exception("Binance 오류")
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/api/v1/testnet/orders/status?symbol=BTCUSDT&orderId=123")
    assert resp.status_code == 500
    assert resp.json()["error_code"] == "INTERNAL_SERVER_ERROR"


def test_cancel_order_by_order_id(client: TestClient):
    with patch("app.services.order_service.cancel_order", new_callable=AsyncMock) as mock:
        from app.models.responses import CancelOrderResponse
        mock.return_value = CancelOrderResponse(
            order_id=123456789,
            symbol="BTCUSDT",
            status="CANCELED",
        )
        resp = client.request(
            "DELETE",
            "/api/v1/testnet/orders",
            json={"symbol": "BTCUSDT", "orderId": 123456789},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["orderId"] == 123456789
    assert data["status"] == "CANCELED"


def test_cancel_order_by_client_order_id(client: TestClient):
    with patch("app.services.order_service.cancel_order", new_callable=AsyncMock) as mock:
        from app.models.responses import CancelOrderResponse
        mock.return_value = CancelOrderResponse(
            order_id=123456789,
            symbol="BTCUSDT",
            status="CANCELED",
        )
        resp = client.request(
            "DELETE",
            "/api/v1/testnet/orders",
            json={"symbol": "BTCUSDT", "origClientOrderId": "demo-001"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELED"


def test_cancel_order_missing_identifier(client: TestClient):
    resp = client.request(
        "DELETE",
        "/api/v1/testnet/orders",
        json={"symbol": "BTCUSDT"},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_cancel_order_missing_symbol(client: TestClient):
    resp = client.request(
        "DELETE",
        "/api/v1/testnet/orders",
        json={"orderId": 123456789},
    )
    assert resp.status_code == 422
