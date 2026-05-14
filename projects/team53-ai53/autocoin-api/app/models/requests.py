from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class SpotOrderRequest(_CamelModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    type: Literal["MARKET", "LIMIT"]
    quantity: str | None = None
    quote_order_qty: str | None = None
    price: str | None = None
    time_in_force: Literal["GTC", "IOC", "FOK"] | None = None

    @model_validator(mode="after")
    def validate_order_params(self) -> "SpotOrderRequest":
        if self.type == "LIMIT":
            if not self.price:
                raise ValueError("LIMIT 주문에는 price가 필요합니다.")
            if not self.quantity:
                raise ValueError("LIMIT 주문에는 quantity가 필요합니다.")
            if not self.time_in_force:
                raise ValueError("LIMIT 주문에는 timeInForce가 필요합니다.")
        if self.type == "MARKET":
            if not self.quantity and not self.quote_order_qty:
                raise ValueError("MARKET 주문에는 quantity 또는 quoteOrderQty가 필요합니다.")
        return self


class CancelOrderRequest(_CamelModel):
    symbol: str
    order_id: int | None = None
    orig_client_order_id: str | None = None

    @model_validator(mode="after")
    def validate_identifier(self) -> "CancelOrderRequest":
        if self.order_id is None and not self.orig_client_order_id:
            raise ValueError("orderId 또는 origClientOrderId 중 하나가 필요합니다.")
        return self
