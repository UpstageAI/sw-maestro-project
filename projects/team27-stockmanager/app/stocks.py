from __future__ import annotations

import datetime as dt
import json
import logging
import math
import random
import time
from pathlib import Path
from typing import Any

from .config import settings
from .kis_client import KISClient


logger = logging.getLogger(__name__)

_VALID_MODES = {"mock", "live"}


def resolve_data_mode() -> str:
    raw = (settings.stock_data_mode or settings.data_mode or "mock").strip().lower()
    if raw in _VALID_MODES:
        return raw
    return "mock"


def is_mock_mode() -> bool:
    return resolve_data_mode() == "mock"


def is_live_mode() -> bool:
    return resolve_data_mode() == "live"


def load_demo_stocks() -> list[dict[str, Any]]:
    path = _demo_data_path()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("demo_stocks.json must contain a list")
    return data


def list_stock_snapshots() -> list[dict[str, Any]]:
    if is_mock_mode():
        return [_build_demo_snapshot(row, include_bars=False) for row in load_demo_stocks()]
    snapshots: list[dict[str, Any]] = []
    for row in load_demo_stocks():
        try:
            snapshots.append(get_stock_snapshot(row["symbol"], include_bars=False))
        except Exception as exc:
            logger.warning("stock list fallback failed for %s: %s", row.get("symbol"), _short_exc(exc))
    return snapshots


def get_stock_snapshot(symbol: str, include_bars: bool = True) -> dict[str, Any]:
    symbol = (symbol or "").strip()
    if not symbol:
        raise ValueError("symbol is required")

    demo_row = _find_demo_row(symbol)
    if is_mock_mode():
        if not demo_row:
            raise StockNotFoundError(symbol)
        return _build_demo_snapshot(demo_row, include_bars=include_bars)

    client = KISClient()
    fetch_status = {"quote": "live", "bars": "live"}
    fallback_reasons: list[str] = []
    quote = None
    quote_source = "live"
    bars: list[Any] = []

    last_exc: Exception | None = None
    for attempt in range(2):
        attempt_reasons: list[str] = []
        try:
            bars = client.get_daily_bars(symbol, days=60)
        except Exception as exc:
            attempt_reasons.append(f"kis_bars={_short_exc(exc)}")
            bars = []

        try:
            quote = client.get_quote(symbol)
            quote_source = "live"
        except Exception as exc:
            attempt_reasons.append(f"kis_quote={_short_exc(exc)}")
            if bars:
                quote = _quote_from_bars(symbol, bars, demo_row.get("name") if demo_row else None)
                quote_source = "derived"
                fetch_status["quote"] = "derived"
            else:
                last_exc = StockNotFoundError(symbol)
                fallback_reasons.extend(attempt_reasons)
                if attempt == 0:
                    time.sleep(0.4)
                    continue
                raise last_exc from exc

        fallback_reasons.extend(attempt_reasons)
        break

    if quote is None:
        raise StockNotFoundError(symbol)

    if not demo_row and float(getattr(quote, "price", 0) or 0) <= 0 and not bars:
        raise StockNotFoundError(symbol)

    if quote_source == "live" and fetch_status["bars"] == "live":
        data_source = "live"
    else:
        data_source = "live"

    if demo_row and _looks_placeholder_name(quote.name, symbol):
        quote.name = str(demo_row.get("name", quote.name))

    record = _quote_to_record(quote)
    record.update(
        {
            "market": (demo_row or {}).get("market", "KOSPI"),
            "updatedAt": (demo_row or {}).get("updatedAt", quote.timestamp.isoformat()),
            "data_mode": resolve_data_mode(),
            "data_source": data_source,
            "fetch_status": fetch_status,
            "fallback_reason": "; ".join(fallback_reasons),
            "kis_auth_mode": client.auth_mode,
            "kis_auth_ready": resolve_data_mode() == "live" and client.has_live_auth,
        }
    )
    if include_bars:
        record["bars"] = [_bar_to_record(bar) for bar in bars]
    return record


class StockNotFoundError(ValueError):
    pass


def _demo_data_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "demo_stocks.json"


def _find_demo_row(symbol: str) -> dict[str, Any] | None:
    for row in load_demo_stocks():
        if str(row.get("symbol")) == symbol:
            return row
    return None


def _build_demo_snapshot(row: dict[str, Any], include_bars: bool = True) -> dict[str, Any]:
    quote = _demo_quote_from_row(row)
    record = _quote_to_record(quote)
    record.update(
        {
            "market": row.get("market", "KOSPI"),
            "updatedAt": row.get("updatedAt", quote.timestamp.isoformat()),
            "data_mode": "mock",
            "data_source": "mock",
            "fetch_status": {"quote": "mock", "bars": "mock"},
            "fallback_reason": "",
            "kis_auth_mode": "mock",
            "kis_auth_ready": False,
        }
    )
    if include_bars:
        record["bars"] = [_bar_to_record(bar) for bar in _demo_bars_from_row(row, 60)]
    return record


def _demo_quote_from_row(row: dict[str, Any]):
    from .kis_client import Quote

    symbol = str(row["symbol"])
    updated_at = _parse_iso(row.get("updatedAt"))
    price = float(row["price"])
    change_rate = float(row.get("changeRate", 0))
    change = float(row.get("change", round(price * change_rate / 100)))
    volume = int(row.get("volume", 0))
    timestamp = updated_at or dt.datetime.now(dt.timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
    return Quote(
        symbol=symbol,
        name=str(row.get("name", symbol)),
        price=price,
        change=change,
        change_rate=change_rate,
        volume=volume,
        timestamp=timestamp,
    )


def _demo_bars_from_row(row: dict[str, Any], days: int) -> list[Any]:
    from .kis_client import DailyBar

    symbol = str(row["symbol"])
    price = float(row["price"])
    change_rate = float(row.get("changeRate", 0))
    updated_at = _parse_iso(row.get("updatedAt")) or dt.datetime.now(dt.timezone.utc)
    end_date = updated_at.date()
    dates: list[dt.date] = []
    cursor = end_date
    while len(dates) < days:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor -= dt.timedelta(days=1)
    dates.reverse()
    seed = f"{symbol}:{price}:{change_rate}"
    rng = random.Random(seed)
    start_price = max(100.0, price * (1 - min(abs(change_rate), 12.0) / 100 - 0.08))
    bars: list[DailyBar] = []
    previous_close = start_price
    for idx, date in enumerate(dates):
        progress = idx / max(1, len(dates) - 1)
        trend = start_price + (price - start_price) * progress
        wave = math.sin((idx + 1) / 4.2 + len(symbol)) * price * 0.012
        close = round(max(1.0, trend + wave), 0)
        if idx == len(dates) - 1:
            close = round(price, 0)
        open_price = round(previous_close, 0)
        high = round(max(open_price, close) * (1 + rng.uniform(0.002, 0.018)), 0)
        low = round(min(open_price, close) * (1 - rng.uniform(0.002, 0.018)), 0)
        volume = int(max(1, float(row.get("volume", 1)) * rng.uniform(0.35, 1.25)))
        bars.append(
            DailyBar(
                date=date,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
        previous_close = close
    return bars


def _quote_from_bars(symbol: str, bars: list[Any], name: str | None = None):
    from .kis_client import Quote

    clean = sorted(bars, key=lambda b: b.date)
    if not clean:
        raise ValueError("bars are required to derive quote")
    last = clean[-1]
    prev = clean[-2] if len(clean) > 1 else last
    prev_close = float(prev.close) if float(prev.close) else float(last.close) or 1.0
    change = float(last.close) - float(prev.close)
    change_rate = (change / prev_close * 100) if prev_close else 0.0
    if not name:
        name = _NAME_MAP.get(symbol, f"종목{symbol}")
    timestamp = dt.datetime.combine(last.date, dt.time(0, 0), tzinfo=dt.timezone.utc)
    return Quote(
        symbol=symbol,
        name=name,
        price=float(last.close),
        change=round(change, 0),
        change_rate=round(change_rate, 2),
        volume=int(last.volume),
        timestamp=timestamp,
    )


def _quote_to_record(quote) -> dict[str, Any]:
    return {
        "symbol": quote.symbol,
        "name": quote.name,
        "price": float(quote.price),
        "change": float(quote.change),
        "changeRate": float(quote.change_rate),
        "change_rate": float(quote.change_rate),
        "volume": int(quote.volume),
        "timestamp": quote.timestamp.isoformat(),
    }


def _bar_to_record(bar) -> dict[str, Any]:
    return {
        "date": bar.date.isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
    }


def _parse_iso(value: Any) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _looks_placeholder_name(name: str | None, symbol: str) -> bool:
    if not name:
        return True
    cleaned = name.strip()
    return cleaned == symbol or cleaned == f"종목{symbol}" or cleaned.isdigit()


def _short_exc(exc: Exception) -> str:
    msg = f"{exc.__class__.__name__}: {exc}"
    return msg if len(msg) <= 180 else msg[:177] + "..."
