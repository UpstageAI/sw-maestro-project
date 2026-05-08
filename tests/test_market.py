from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_get_price_success(client: TestClient):
    with patch("app.services.market_service.get_price", new_callable=AsyncMock) as mock:
        from app.models.responses import PriceResponse
        mock.return_value = PriceResponse(symbol="BTCUSDT", price="65000.12")
        resp = client.get("/api/v1/testnet/ticker/price?symbol=BTCUSDT")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["price"] == "65000.12"


def test_get_price_missing_symbol(client: TestClient):
    resp = client.get("/api/v1/testnet/ticker/price")
    assert resp.status_code == 422


def test_get_price_binance_failure(client: TestClient):
    with patch("app.services.market_service.get_price", new_callable=AsyncMock) as mock:
        mock.side_effect = Exception("Binance 오류")
        from fastapi.testclient import TestClient as TC
        from app.main import app
        with TC(app, raise_server_exceptions=False) as c:
            resp = c.get("/api/v1/testnet/ticker/price?symbol=BTCUSDT")
    assert resp.status_code == 500
    assert resp.json()["error_code"] == "INTERNAL_SERVER_ERROR"


def test_get_book_success(client: TestClient):
    with patch("app.services.market_service.get_book", new_callable=AsyncMock) as mock:
        from app.models.responses import BookDepth, BookResponse
        mock.return_value = BookResponse(
            symbol="BTCUSDT",
            bid_price="64999.99",
            bid_qty="0.12",
            ask_price="65000.13",
            ask_qty="0.45",
            depth=BookDepth(
                last_update_id=123456,
                bids=[("64999.99", "0.12")],
                asks=[("65000.13", "0.45")],
            ),
        )
        resp = client.get("/api/v1/testnet/ticker/book?symbol=BTCUSDT")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["bidPrice"] == "64999.99"
    assert data["askPrice"] == "65000.13"
    assert data["depth"]["lastUpdateId"] == 123456
    assert data["depth"]["bids"][0] == ["64999.99", "0.12"]


def test_get_book_missing_symbol(client: TestClient):
    resp = client.get("/api/v1/testnet/ticker/book")
    assert resp.status_code == 422


def test_get_klines_success(client: TestClient):
    with patch("app.services.market_service.get_klines", new_callable=AsyncMock) as mock:
        from app.models.responses import KlineItem, KlinesResponse
        mock.return_value = KlinesResponse(
            symbol="BTCUSDT",
            interval="1m",
            items=[
                KlineItem(
                    open_time=1715000000000,
                    open="64950.00",
                    high="65100.00",
                    low="64880.00",
                    close="65000.12",
                    volume="12.34",
                )
            ],
        )
        resp = client.get("/api/v1/testnet/klines?symbol=BTCUSDT&interval=1m&limit=5")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTCUSDT"
    assert data["interval"] == "1m"
    assert len(data["items"]) == 1
    assert data["items"][0]["openTime"] == 1715000000000


def test_get_klines_missing_params(client: TestClient):
    resp = client.get("/api/v1/testnet/klines?symbol=BTCUSDT")
    assert resp.status_code == 422


def test_get_klines_default_limit(client: TestClient):
    with patch("app.services.market_service.get_klines", new_callable=AsyncMock) as mock:
        from app.models.responses import KlinesResponse
        mock.return_value = KlinesResponse(symbol="BTCUSDT", interval="1m", items=[])
        client.get("/api/v1/testnet/klines?symbol=BTCUSDT&interval=1m")
        # get_klines(db, symbol, interval, limit, settings) — limit은 4번째(index 3)
        limit_arg = mock.call_args.args[3] if mock.call_args.args else mock.call_args.kwargs.get("limit")
        assert limit_arg == 100
