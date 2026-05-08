import httpx

from app.config import Settings
from app.models.responses import BalanceItem, BalanceResponse
from app.services.binance_auth_service import build_signed_params


async def get_account(settings: Settings) -> BalanceResponse:
    params = build_signed_params(settings.binance_testnet_secret_key, {})
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.binance_testnet_rest_base_url}/v3/account",
            headers={"X-MBX-APIKEY": settings.binance_testnet_api_key},
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    balances = [
        BalanceItem(asset=b["asset"], free=b["free"], locked=b["locked"])
        for b in data.get("balances", [])
        if float(b["free"]) > 0 or float(b["locked"]) > 0
    ]
    return BalanceResponse(balances=balances)
