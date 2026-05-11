from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.ai import ResumeCommandPayload
from app.models.requests import AutoOrderRequest, AutoSessionStartRequest, CancelOrderRequest, SpotOrderRequest
from app.models.responses import AutoOrderRunResponse, AutoTradingSessionResponse, CancelOrderResponse, OrderRunResponse, OrderStatusResponse, RunReportResponse
from app.services import auto_session_service, order_service, report_service

router = APIRouter()


@router.post("/orders", response_model=OrderRunResponse, status_code=200)
async def create_order(
    req: SpotOrderRequest,
    db: Session = Depends(get_db),
) -> OrderRunResponse:
    return await order_service.create_order(db, req, settings)


@router.post("/orders/auto", response_model=AutoOrderRunResponse, status_code=200)
async def create_auto_order(
    req: AutoOrderRequest,
    db: Session = Depends(get_db),
) -> AutoOrderRunResponse:
    return await order_service.create_auto_order(db, req, settings)


@router.post("/orders/auto/session/start", response_model=AutoTradingSessionResponse, status_code=200)
async def start_auto_session(payload: AutoSessionStartRequest) -> AutoTradingSessionResponse:
    try:
        return await auto_session_service.start_auto_session(payload, settings)
    except ValueError as exc:
        if str(exc) == "ACTIVE_AUTO_SESSION_EXISTS":
            raise HTTPException(status_code=409, detail="이미 실행 중인 자연어 자동매매 세션이 있습니다.") from exc
        raise


@router.post("/orders/auto/session/stop", response_model=AutoTradingSessionResponse, status_code=200)
async def stop_auto_session() -> AutoTradingSessionResponse:
    return await auto_session_service.stop_auto_session()


@router.get("/orders/auto/session", response_model=AutoTradingSessionResponse, status_code=200)
async def get_auto_session() -> AutoTradingSessionResponse:
    return auto_session_service.get_auto_session_status()


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
