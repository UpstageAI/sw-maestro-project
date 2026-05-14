import asyncio
import logging

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.crud import save_price_snapshot
from app.models.responses import BookDepth, BookResponse, KlineItem, KlinesResponse, PriceResponse

logger = logging.getLogger(__name__)


async def get_price(db: Session, symbol: str, settings: Settings) -> PriceResponse:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.binance_testnet_rest_base_url}/v3/ticker/price",
                params={"symbol": symbol},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Binance price API error: status=%s body=%s", e.response.status_code, e.response.text)
        raise
    except Exception:
        logger.exception("Unexpected error during Binance price call")
        raise

    result = PriceResponse(symbol=data["symbol"], price=data["price"])
    save_price_snapshot(db, symbol=symbol, snapshot_json=result.model_dump())
    return result


async def get_book(db: Session, symbol: str, settings: Settings) -> BookResponse:
    try:
        async with httpx.AsyncClient() as client:
            book_resp, depth_resp = await _fetch_book_and_depth(client, symbol, settings)
    except httpx.HTTPStatusError as e:
        logger.error("Binance book API error: status=%s body=%s", e.response.status_code, e.response.text)
        raise
    except Exception:
        logger.exception("Unexpected error during Binance book call")
        raise

    result = BookResponse(
        symbol=symbol,
        bid_price=book_resp["bidPrice"],
        bid_qty=book_resp["bidQty"],
        ask_price=book_resp["askPrice"],
        ask_qty=book_resp["askQty"],
        depth=BookDepth(
            last_update_id=depth_resp["lastUpdateId"],
            bids=[tuple(b) for b in depth_resp["bids"]],
            asks=[tuple(a) for a in depth_resp["asks"]],
        ),
    )
    save_price_snapshot(db, symbol=symbol, snapshot_json=result.model_dump())
    return result


async def _fetch_book_and_depth(client: httpx.AsyncClient, symbol: str, settings: Settings) -> tuple[dict, dict]:
    book_task = client.get(
        f"{settings.binance_testnet_rest_base_url}/v3/ticker/bookTicker",
        params={"symbol": symbol},
        timeout=10,
    )
    depth_task = client.get(
        f"{settings.binance_testnet_rest_base_url}/v3/depth",
        params={"symbol": symbol, "limit": 5},
        timeout=10,
    )
    book_r, depth_r = await asyncio.gather(book_task, depth_task)
    book_r.raise_for_status()
    depth_r.raise_for_status()
    return book_r.json(), depth_r.json()


async def get_klines(db: Session, symbol: str, interval: str, limit: int, settings: Settings) -> KlinesResponse:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.binance_testnet_rest_base_url}/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
                timeout=10,
            )
            resp.raise_for_status()
            raw = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Binance klines API error: status=%s body=%s", e.response.status_code, e.response.text)
        raise
    except Exception:
        logger.exception("Unexpected error during Binance klines call")
        raise

    items = [
        KlineItem(
            open_time=k[0],
            open=k[1],
            high=k[2],
            low=k[3],
            close=k[4],
            volume=k[5],
        )
        for k in raw
    ]
    result = KlinesResponse(symbol=symbol, interval=interval, items=items)
    save_price_snapshot(db, symbol=symbol, snapshot_json=result.model_dump())
    return result
