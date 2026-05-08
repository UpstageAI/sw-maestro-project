from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.db.crud import save_balance_snapshot
from app.models.responses import BalanceResponse
from app.services import account_service

router = APIRouter()


@router.get("/account", response_model=BalanceResponse)
async def get_account(db: Session = Depends(get_db)) -> BalanceResponse:
    result = await account_service.get_account(settings)
    save_balance_snapshot(db, result.model_dump())
    return result
