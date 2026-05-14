from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.responses import KlinesResponse
from app.services import market_service

router = APIRouter()


@router.get("/klines", response_model=KlinesResponse, status_code=200)
async def get_klines(
    symbol: str,
    interval: str,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> KlinesResponse:
    return await market_service.get_klines(db, symbol, interval, limit, settings)
