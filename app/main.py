import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.models.health import HealthResponse

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
