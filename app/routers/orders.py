from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.requests import CancelOrderRequest
from app.models.responses import CancelOrderResponse, OrderStatusResponse
from app.services import order_service

router = APIRouter()


@router.get("/orders/status", response_model=OrderStatusResponse, status_code=200)
async def get_order_status(
    symbol: str,
    order_id: int | None = Query(default=None, alias="orderId"),
    orig_client_order_id: str | None = Query(default=None, alias="origClientOrderId"),
    db: Session = Depends(get_db),
) -> OrderStatusResponse:
    if order_id is None and orig_client_order_id is None:
        raise HTTPException(status_code=422, detail="orderId 또는 origClientOrderId 중 하나가 필요합니다.")
    return await order_service.get_order_status(db, symbol, order_id, orig_client_order_id, settings)


@router.delete("/orders", response_model=CancelOrderResponse, status_code=200)
async def cancel_order(
    req: CancelOrderRequest,
    db: Session = Depends(get_db),
) -> CancelOrderResponse:
    return await order_service.cancel_order(db, req, settings)
