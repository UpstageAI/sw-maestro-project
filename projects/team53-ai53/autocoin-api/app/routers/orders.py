from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.ai import ResumeCommandPayload
from app.models.requests import CancelOrderRequest, SpotOrderRequest
from app.models.responses import CancelOrderResponse, OrderRunResponse, OrderStatusResponse, RunReportResponse
from app.services import order_service, report_service

router = APIRouter()


@router.post("/orders", response_model=OrderRunResponse, status_code=200)
async def create_order(
    req: SpotOrderRequest,
    db: Session = Depends(get_db),
) -> OrderRunResponse:
    return await order_service.create_order(db, req, settings)


@router.post("/orders/resume", response_model=OrderRunResponse, status_code=200)
async def resume_order(
    payload: ResumeCommandPayload,
    db: Session = Depends(get_db),
) -> OrderRunResponse:
    return await order_service.resume_order(db, payload, settings)


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


@router.get("/orders/report", response_model=RunReportResponse, status_code=200)
async def get_order_report(
    run_id: str = Query(alias="runId"),
    db: Session = Depends(get_db),
) -> RunReportResponse:
    return report_service.get_run_report(db, run_id)
