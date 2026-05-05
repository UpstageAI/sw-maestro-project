import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Coin Agent BE",
    description="Binance Spot Testnet 전용 백엔드 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    create_tables()
    logger.info("DB tables created. App env: %s", settings.app_env)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


# Routers registered in later phases
# from app.routers import account, ticker, klines, orders, stream
# app.include_router(account.router, prefix="/api/v1/testnet")
# app.include_router(ticker.router, prefix="/api/v1/testnet")
# app.include_router(klines.router, prefix="/api/v1/testnet")
# app.include_router(orders.router, prefix="/api/v1/testnet")
# app.include_router(stream.router, prefix="/api/v1/testnet")
