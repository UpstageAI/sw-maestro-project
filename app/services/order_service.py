import logging

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.crud import (
    get_spot_order_by_binance_id,
    save_cancel_log,
    save_order_status_log,
    save_spot_order,
    update_spot_order_status,
)
from app.models.requests import CancelOrderRequest
from app.models.responses import CancelOrderResponse, OrderStatusResponse
from app.services.binance_auth_service import build_signed_params

logger = logging.getLogger(__name__)


async def get_order_status(
    db: Session,
    symbol: str,
    order_id: int | None,
    orig_client_order_id: str | None,
    settings: Settings,
) -> OrderStatusResponse:
    params: dict = {"symbol": symbol}
    if order_id is not None:
        params["orderId"] = order_id
    else:
        params["origClientOrderId"] = orig_client_order_id

    signed = build_signed_params(settings.binance_testnet_secret_key, params)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.binance_testnet_rest_base_url}/v3/order",
                headers={"X-MBX-APIKEY": settings.binance_testnet_api_key},
                params=signed,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Binance order status error: status=%s body=%s", e.response.status_code, e.response.text)
        raise
    except Exception:
        logger.exception("Unexpected error during Binance order status call")
        raise

    # 내부 DB에 해당 주문이 있을 때만 status log 저장
    binance_order_id = str(data.get("orderId", ""))
    existing = get_spot_order_by_binance_id(db, binance_order_id)
    if existing:
        save_order_status_log(db, order_id=existing.order_id, status_json=data)

    return OrderStatusResponse(
        order_id=data["orderId"],
        symbol=data["symbol"],
        status=data["status"],
        executed_qty=data["executedQty"],
    )


async def cancel_order(
    db: Session,
    req: CancelOrderRequest,
    settings: Settings,
) -> CancelOrderResponse:
    params: dict = {"symbol": req.symbol}
    if req.order_id is not None:
        params["orderId"] = req.order_id
    else:
        params["origClientOrderId"] = req.orig_client_order_id

    signed = build_signed_params(settings.binance_testnet_secret_key, params)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{settings.binance_testnet_rest_base_url}/v3/order",
                headers={"X-MBX-APIKEY": settings.binance_testnet_api_key},
                params=signed,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Binance cancel order error: status=%s body=%s", e.response.status_code, e.response.text)
        raise
    except Exception:
        logger.exception("Unexpected error during Binance cancel order call")
        raise

    binance_order_id = str(data.get("orderId", ""))
    existing = get_spot_order_by_binance_id(db, binance_order_id)
    if existing:
        update_spot_order_status(db, order_id=existing.order_id, status="CANCELED", response_json=data)
        order_pk = existing.order_id
    else:
        order_row = save_spot_order(
            db,
            symbol=req.symbol,
            request_json=req.model_dump(),
            binance_order_id=binance_order_id,
            status="CANCELED",
        )
        order_pk = order_row.order_id

    save_cancel_log(db, order_id=order_pk, cancel_json=data)
    return CancelOrderResponse(
        order_id=data["orderId"],
        symbol=data["symbol"],
        status=data["status"],
    )
