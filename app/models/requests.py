from typing import Literal

from pydantic import BaseModel, model_validator


class SpotOrderRequest(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    type: Literal["MARKET", "LIMIT"]
    quantity: str | None = None
    quote_order_qty: str | None = None
    price: str | None = None
    time_in_force: str | None = None

    @model_validator(mode="after")
    def validate_order_params(self) -> "SpotOrderRequest":
        if self.type == "LIMIT":
            if not self.price:
                raise ValueError("LIMIT 주문에는 price가 필요합니다.")
            if not self.quantity:
                raise ValueError("LIMIT 주문에는 quantity가 필요합니다.")
            if not self.time_in_force:
                raise ValueError("LIMIT 주문에는 time_in_force가 필요합니다.")
        if self.type == "MARKET":
            if not self.quantity and not self.quote_order_qty:
                raise ValueError("MARKET 주문에는 quantity 또는 quote_order_qty가 필요합니다.")
        return self


class CancelOrderRequest(BaseModel):
    symbol: str
    order_id: int | None = None
    orig_client_order_id: str | None = None

    @model_validator(mode="after")
    def validate_identifier(self) -> "CancelOrderRequest":
        if not self.order_id and not self.orig_client_order_id:
            raise ValueError("order_id 또는 orig_client_order_id 중 하나가 필요합니다.")
        return self
