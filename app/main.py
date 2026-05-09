import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_tables
from app.models.health import HealthResponse
from app.models.responses import ErrorResponse
from app.routers import account, config, klines, orders, stream, ticker
from app.services import stream_service

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    create_tables()
    logger.info("DB tables created. App env: %s", settings.app_env)
    stream_service.start_stream(settings.binance_testnet_ws_stream_url)
    yield
    await stream_service.stop_stream()


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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return _error_response(
        error_code="VALIDATION_ERROR" if exc.status_code == 422 else "REQUEST_FAILED",
        message=str(exc.detail),
        detail=None,
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    messages = "; ".join(
        f"{' → '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    return _error_response(
        error_code="VALIDATION_ERROR",
        message="요청 파라미터가 올바르지 않습니다.",
        detail=messages,
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


app.include_router(account.router, prefix="/api/v1/testnet")
app.include_router(config.router, prefix="/api/v1/testnet")
app.include_router(ticker.router, prefix="/api/v1/testnet")
app.include_router(klines.router, prefix="/api/v1/testnet")
app.include_router(orders.router, prefix="/api/v1/testnet")
app.include_router(stream.router, prefix="/api/v1/testnet")
