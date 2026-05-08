from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.responses import BookResponse, PriceResponse
from app.services import market_service

router = APIRouter()


@router.get("/ticker/price", response_model=PriceResponse, status_code=200)
async def get_price(symbol: str, db: Session = Depends(get_db)) -> PriceResponse:
    return await market_service.get_price(db, symbol, settings)


@router.get("/ticker/book", response_model=BookResponse, status_code=200)
async def get_book(symbol: str, db: Session = Depends(get_db)) -> BookResponse:
    return await market_service.get_book(db, symbol, settings)
