import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_tables
from app.models.health import HealthResponse
from app.models.responses import ErrorResponse

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    create_tables()
    logger.info("DB tables created. App env: %s", settings.app_env)
    yield


app = FastAPI(
    title="Coin Agent BE",
    description="Binance Spot Testnet 전용 백엔드 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_response(error_code: str, message: str, detail: str | None, status_code: int) -> JSONResponse:
    body = ErrorResponse(
        error_code=error_code,
        message=message,
        detail=detail,
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        error_code="VALIDATION_ERROR",
        message="요청 파라미터가 올바르지 않습니다.",
        detail=str(exc.errors()),
        status_code=422,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    detail = str(exc) if settings.app_env == "local" else None
    return _error_response(
        error_code="INTERNAL_SERVER_ERROR",
        message="서버 내부 오류가 발생했습니다.",
        detail=detail,
        status_code=500,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", env=settings.app_env)


# Routers registered in later phases
# from app.routers import account, ticker, klines, orders, stream
# app.include_router(account.router, prefix="/api/v1/testnet")
# app.include_router(ticker.router, prefix="/api/v1/testnet")
# app.include_router(klines.router, prefix="/api/v1/testnet")
# app.include_router(orders.router, prefix="/api/v1/testnet")
# app.include_router(stream.router, prefix="/api/v1/testnet")
