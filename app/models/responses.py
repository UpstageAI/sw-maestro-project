from typing import Any, Literal

from pydantic import BaseModel


class BalanceItem(BaseModel):
    asset: str
    free: str
    locked: str


class BalanceResponse(BaseModel):
    balances: list[BalanceItem]


class PriceResponse(BaseModel):
    symbol: str
    price: str


class BookDepth(BaseModel):
    last_update_id: int
    bids: list[tuple[str, str]]
    asks: list[tuple[str, str]]


class BookResponse(BaseModel):
    symbol: str
    bid_price: str
    bid_qty: str
    ask_price: str
    ask_qty: str
    depth: BookDepth


class KlineItem(BaseModel):
    open_time: int
    open: str
    high: str
    low: str
    close: str
    volume: str


class KlinesResponse(BaseModel):
    symbol: str
    interval: str
    items: list[KlineItem]


_OrderStatus = Literal["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "PENDING_CANCEL", "REJECTED", "EXPIRED"]


class OrderResponse(BaseModel):
    order_id: int
    symbol: str
    status: _OrderStatus
    type: str
    side: str


class OrderStatusResponse(BaseModel):
    order_id: int
    symbol: str
    status: _OrderStatus
    executed_qty: str


class CancelOrderResponse(BaseModel):
    order_id: int
    symbol: str
    status: _OrderStatus


class StreamStatusResponse(BaseModel):
    connected: bool
    stream_name: str | None = None
    last_event: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: str | None = None
    request_id: str | None = None
    timestamp: str | None = None
