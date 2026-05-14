import pytest

from app.models.requests import CancelOrderRequest, SpotOrderRequest
from app.models.responses import (
    BookDepth,
    BookResponse,
    CancelOrderResponse,
    KlineItem,
    KlinesResponse,
    OrderResponse,
    OrderStatusResponse,
)


def test_spot_order_request_accepts_camel_case():
    req = SpotOrderRequest.model_validate(
        {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "50"}
    )
    assert req.quote_order_qty == "50"


def test_spot_order_request_limit_serializes_as_camel_case():
    req = SpotOrderRequest(
        symbol="BTCUSDT",
        side="BUY",
        type="LIMIT",
        price="64000",
        quantity="0.001",
        time_in_force="GTC",
    )
    dumped = req.model_dump(by_alias=True, exclude_none=True)
    assert dumped == {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "price": "64000",
        "quantity": "0.001",
        "timeInForce": "GTC",
    }


def test_spot_order_request_limit_requires_price_quantity_tif():
    with pytest.raises(ValueError):
        SpotOrderRequest(symbol="BTCUSDT", side="BUY", type="LIMIT")


def test_spot_order_request_market_requires_qty_or_quote_qty():
    with pytest.raises(ValueError):
        SpotOrderRequest(symbol="BTCUSDT", side="BUY", type="MARKET")


def test_cancel_order_request_camel_case():
    req = CancelOrderRequest.model_validate(
        {"symbol": "BTCUSDT", "origClientOrderId": "demo-001"}
    )
    assert req.orig_client_order_id == "demo-001"


def test_cancel_order_request_requires_identifier():
    with pytest.raises(ValueError):
        CancelOrderRequest(symbol="BTCUSDT")


def test_book_response_serializes_as_camel_case():
    resp = BookResponse(
        symbol="BTCUSDT",
        bid_price="64999.99",
        bid_qty="0.12",
        ask_price="65000.13",
        ask_qty="0.45",
        depth=BookDepth(last_update_id=1, bids=[("64999.99", "0.12")], asks=[("65000.13", "0.45")]),
    )
    dumped = resp.model_dump(by_alias=True)
    assert dumped["bidPrice"] == "64999.99"
    assert dumped["askQty"] == "0.45"
    assert dumped["depth"]["lastUpdateId"] == 1


def test_klines_response_open_time_camel_case():
    resp = KlinesResponse(
        symbol="BTCUSDT",
        interval="1m",
        items=[
            KlineItem(open_time=1715000000000, open="1", high="2", low="0.5", close="1.5", volume="10"),
        ],
    )
    dumped = resp.model_dump(by_alias=True)
    assert dumped["items"][0]["openTime"] == 1715000000000


def test_order_response_camel_case():
    resp = OrderResponse(order_id=123, symbol="BTCUSDT", status="NEW", type="LIMIT", side="BUY")
    assert resp.model_dump(by_alias=True)["orderId"] == 123


def test_order_status_response_executed_qty_camel_case():
    resp = OrderStatusResponse(order_id=1, symbol="BTCUSDT", status="FILLED", executed_qty="0.001")
    assert resp.model_dump(by_alias=True)["executedQty"] == "0.001"


def test_cancel_order_response_camel_case():
    resp = CancelOrderResponse(order_id=1, symbol="BTCUSDT", status="CANCELED")
    assert resp.model_dump(by_alias=True)["orderId"] == 1
