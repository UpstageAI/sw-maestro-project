from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.responses import BalanceResponse
from app.services import account_service

router = APIRouter()


@router.get("/account", response_model=BalanceResponse, status_code=200)
async def get_account(db: Session = Depends(get_db)) -> BalanceResponse:
    return await account_service.get_account(db, settings)
