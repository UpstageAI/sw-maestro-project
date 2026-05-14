import logging

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.crud import save_balance_snapshot
from app.models.responses import BalanceItem, BalanceResponse
from app.services.binance_auth_service import build_signed_params

logger = logging.getLogger(__name__)


async def get_account(db: Session, settings: Settings) -> BalanceResponse:
    params = build_signed_params(settings.binance_testnet_secret_key, {})
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.binance_testnet_rest_base_url}/v3/account",
                headers={"X-MBX-APIKEY": settings.binance_testnet_api_key},
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Binance API error: status=%s body=%s", e.response.status_code, e.response.text)
        raise
    except Exception:
        logger.exception("Unexpected error during Binance account call")
        raise

    balances = [
        BalanceItem(asset=b["asset"], free=b["free"], locked=b["locked"])
        for b in data.get("balances", [])
        if float(b["free"]) > 0 or float(b["locked"]) > 0
    ]
    result = BalanceResponse(balances=balances)
    save_balance_snapshot(db, result.model_dump())
    return result
