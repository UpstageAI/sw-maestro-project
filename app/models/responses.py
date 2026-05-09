from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class BalanceItem(_CamelModel):
    asset: str
    free: str
    locked: str


class BalanceResponse(_CamelModel):
    balances: list[BalanceItem]


class PriceResponse(_CamelModel):
    symbol: str
    price: str


class BookDepth(_CamelModel):
    last_update_id: int
    bids: list[tuple[str, str]]
    asks: list[tuple[str, str]]


class BookResponse(_CamelModel):
    symbol: str
    bid_price: str
    bid_qty: str
    ask_price: str
    ask_qty: str
    depth: BookDepth


class KlineItem(_CamelModel):
    open_time: int
    open: str
    high: str
    low: str
    close: str
    volume: str


class KlinesResponse(_CamelModel):
    symbol: str
    interval: str
    items: list[KlineItem]


_OrderStatus = Literal["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]


class OrderResponse(_CamelModel):
    order_id: int
    symbol: str
    status: _OrderStatus
    type: str
    side: str


class OrderStatusResponse(_CamelModel):
    order_id: int
    symbol: str
    status: _OrderStatus
    executed_qty: str


class CancelOrderResponse(_CamelModel):
    order_id: int
    symbol: str
    status: _OrderStatus


class OrderRunResponse(_CamelModel):
    run_id: str
    lifecycle_status: str
    hold_reason: str | None = None
    order_id: int | None = None
    symbol: str | None = None
    status: _OrderStatus | None = None
    type: str | None = None
    side: str | None = None
    reason_codes: list[str] = []


class RunReportResponse(_CamelModel):
    run_id: str
    report: dict[str, Any]


class StreamStatusResponse(_CamelModel):
    connected: bool
    stream_name: str | None = None
    last_event: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: str | None = None
    request_id: str | None = None
    timestamp: str | None = None
