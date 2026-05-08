from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def test_get_account_success(client: TestClient):
    mock_response = {
        "makerCommission": 0,
        "takerCommission": 0,
        "canTrade": True,
        "balances": [
            {"asset": "USDT", "free": "10000.00000000", "locked": "0.00000000"},
            {"asset": "BTC", "free": "0.50000000", "locked": "0.00000000"},
            {"asset": "ETH", "free": "0.00000000", "locked": "0.00000000"},
        ],
    }
    with patch("app.services.account_service.get_account", new_callable=AsyncMock) as mock_get:
        from app.models.responses import BalanceItem, BalanceResponse
        mock_get.return_value = BalanceResponse(
            balances=[
                BalanceItem(asset="USDT", free="10000.00000000", locked="0.00000000"),
                BalanceItem(asset="BTC", free="0.50000000", locked="0.00000000"),
            ]
        )
        resp = client.get("/api/v1/testnet/account")

    assert resp.status_code == 200
    data = resp.json()
    assert "balances" in data
    assert len(data["balances"]) == 2
    assert data["balances"][0]["asset"] == "USDT"
    assert data["balances"][0]["free"] == "10000.00000000"


def test_get_account_returns_only_nonzero_balances(client: TestClient):
    with patch("app.services.account_service.get_account", new_callable=AsyncMock) as mock_get:
        from app.models.responses import BalanceItem, BalanceResponse
        mock_get.return_value = BalanceResponse(
            balances=[
                BalanceItem(asset="USDT", free="10000.00000000", locked="0.00000000"),
            ]
        )
        resp = client.get("/api/v1/testnet/account")

    assert resp.status_code == 200
    assert len(resp.json()["balances"]) == 1


def test_get_account_binance_failure_returns_error():
    from fastapi.testclient import TestClient
    from app.main import app
    with patch("app.services.account_service.get_account", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Binance 연결 실패")
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/api/v1/testnet/account")

    assert resp.status_code == 500
    data = resp.json()
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"


def test_get_account_response_has_camel_case_keys(client: TestClient):
    with patch("app.services.account_service.get_account", new_callable=AsyncMock) as mock_get:
        from app.models.responses import BalanceItem, BalanceResponse
        mock_get.return_value = BalanceResponse(
            balances=[BalanceItem(asset="BTC", free="1.0", locked="0.0")]
        )
        resp = client.get("/api/v1/testnet/account")

    assert resp.status_code == 200
    balance = resp.json()["balances"][0]
    assert "asset" in balance
    assert "free" in balance
    assert "locked" in balance
