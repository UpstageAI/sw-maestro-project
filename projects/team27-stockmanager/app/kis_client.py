from __future__ import annotations

import datetime as dt
import json
import logging
import re
import random
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Optional

import httpx
import pandas as pd

from .config import settings


logger = logging.getLogger(__name__)


@dataclass
class Quote:
    symbol: str
    name: str
    price: float
    change: float
    change_rate: float
    volume: int
    timestamp: dt.datetime


@dataclass
class DailyBar:
    date: dt.date
    open: float
    high: float
    low: float
    close: float
    volume: int


_NAME_MAP = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "035720": "카카오",
    "005380": "현대차",
    "051910": "LG화학",
    "207940": "삼성바이오로직스",
}


class KISClient:
    """한국투자증권 OpenAPI 얇은 래퍼. 데이터 모드가 mock이면 KIS를 호출하지 않는다."""

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._token_expiry: Optional[dt.datetime] = None
        self._load_cached_auth()

    @property
    def use_mock(self) -> bool:
        mode = (settings.stock_data_mode or settings.data_mode or "mock").strip().lower()
        return mode != "live" or not settings.kis_app_key or not settings.kis_app_secret

    @property
    def base_url(self) -> str:
        return settings.kis_base_url.rstrip("/")

    @property
    def has_live_auth(self) -> bool:
        if self._token and self._token_expiry and dt.datetime.now(dt.timezone.utc) < self._token_expiry:
            return True
        return bool(settings.kis_app_key and settings.kis_app_secret)

    @property
    def auth_mode(self) -> str:
        return "client_credentials"

    def _ensure_token(self) -> str:
        now = dt.datetime.now(dt.timezone.utc)
        if self._token and self._token_expiry and now < self._token_expiry:
            return self._token
        try:
            resp = httpx.post(
                f"{self.base_url}/oauth2/tokenP",
                headers={"Content-Type": "application/json"},
                json={
                    "grant_type": "client_credentials",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            ttl = int(data.get("expires_in", 3600)) - 60
            self._token_expiry = now + dt.timedelta(seconds=max(60, ttl))
            self._save_cached_auth()
            return self._token
        except Exception as exc:
            logger.warning("KIS token 발급 실패: %s", _short_exc(exc))
            raise

    def get_quote(self, symbol: str) -> Quote:
        if self.use_mock:
            return _mock_quote(symbol)
        token = self._ensure_token()
        resp = httpx.get(
            f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers={
                "Content-Type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
                "tr_id": "FHKST01010100",
            },
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
            timeout=10.0,
        )
        resp.raise_for_status()
        d = resp.json().get("output") or {}
        return Quote(
            symbol=symbol,
            name=d.get("hts_kor_isnm") or _NAME_MAP.get(symbol, symbol),
            price=float(d.get("stck_prpr", 0) or 0),
            change=round(float(d.get("stck_prpr", 0) or 0) * float(d.get("prdy_ctrt", 0) or 0) / 100, 0),
            change_rate=float(d.get("prdy_ctrt", 0) or 0),
            volume=int(float(d.get("acml_vol", 0) or 0)),
            timestamp=dt.datetime.now(dt.timezone.utc),
        )

    def get_daily_bars(self, symbol: str, days: int = 60) -> list[DailyBar]:
        if self.use_mock:
            return _mock_daily_bars(symbol, days)
        token = self._ensure_token()
        bars = self._get_daily_bars_by_price(symbol, days, token)
        if bars:
            return bars
        bars = self._get_daily_bars_by_itemchart(symbol, days, token)
        if bars:
            return bars
        raise ValueError(f"KIS daily bars not found for {symbol}")

    def _get_daily_bars_by_price(self, symbol: str, days: int, token: str) -> list[DailyBar]:
        try:
            resp = httpx.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price",
                headers={
                    "Content-Type": "application/json",
                    "authorization": f"Bearer {token}",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                    "tr_id": "FHKST01010400",
                },
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_PERIOD_DIV_CODE": "D",
                    "FID_ORG_ADJ_PRC": "1",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            rows = resp.json().get("output") or []
            return self._rows_to_bars(rows)[-days:]
        except Exception as exc:
            logger.warning("KIS daily price 실패(%s): %s", symbol, _short_exc(exc))
            return []

    def _get_daily_bars_by_itemchart(self, symbol: str, days: int, token: str) -> list[DailyBar]:
        end = dt.date.today()
        start = end - dt.timedelta(days=max(days * 2, 120))
        try:
            resp = httpx.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                headers={
                    "Content-Type": "application/json",
                    "authorization": f"Bearer {token}",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                    "tr_id": "FHKST03010100",
                },
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
                    "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
                    "FID_PERIOD_DIV_CODE": "D",
                    "FID_ORG_ADJ_PRC": "1",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            rows = resp.json().get("output2") or []
            return self._rows_to_bars(rows)[-days:]
        except Exception as exc:
            logger.warning("KIS daily itemchart 실패(%s): %s", symbol, _short_exc(exc))
            return []

    def _rows_to_bars(self, rows: list[dict]) -> list[DailyBar]:
        bars: list[DailyBar] = []
        for r in rows:
            try:
                date_text = r.get("stck_bsop_date") or r.get("xymd") or r.get("date")
                if not date_text:
                    continue
                bars.append(
                    DailyBar(
                        date=dt.datetime.strptime(str(date_text), "%Y%m%d").date(),
                        open=float(r.get("stck_oprc") or r.get("open") or 0),
                        high=float(r.get("stck_hgpr") or r.get("high") or 0),
                        low=float(r.get("stck_lwpr") or r.get("low") or 0),
                        close=float(r.get("stck_clpr") or r.get("close") or 0),
                        volume=int(float(r.get("acml_vol") or r.get("volume") or 0)),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        bars.sort(key=lambda b: b.date)
        return bars

    def _load_cached_auth(self) -> None:
        path = Path(settings.kis_token_cache_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
        except Exception:
            return
        token = data.get("access_token")
        expires_at = data.get("expires_at")
        if token and expires_at:
            try:
                parsed = dt.datetime.fromisoformat(expires_at)
            except ValueError:
                return
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            if dt.datetime.now(dt.timezone.utc) < parsed:
                self._token = str(token)
                self._token_expiry = parsed

    def _save_cached_auth(self) -> None:
        if not self._token or not self._token_expiry:
            return
        path = Path(settings.kis_token_cache_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "access_token": self._token,
            "expires_at": self._token_expiry.isoformat(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def get_public_quote(self, symbol: str) -> Quote:
        df = _naver_daily_page(symbol, 1)
        rows = df.dropna(subset=["날짜", "종가"])
        if rows.empty:
            raise ValueError(f"naver quote not found for {symbol}")
        return _row_to_quote(symbol, rows.iloc[0], _naver_company_name(symbol))

    def get_public_daily_bars(self, symbol: str, days: int = 60) -> list[DailyBar]:
        bars: list[DailyBar] = []
        seen: set[dt.date] = set()
        page = 1
        max_pages = max(6, (days // 10) + 2)
        while len(bars) < days and page <= max_pages:
            df = _naver_daily_page(symbol, page)
            if df.empty:
                break
            added = 0
            for _, row in df.iterrows():
                try:
                    bar = _row_to_daily_bar(row)
                except ValueError:
                    continue
                if bar.date in seen:
                    continue
                seen.add(bar.date)
                bars.append(bar)
                added += 1
                if len(bars) >= days:
                    break
            if added == 0:
                break
            page += 1
        bars.sort(key=lambda b: b.date)
        if not bars:
            raise ValueError(f"naver daily bars not found for {symbol}")
        return bars[-days:]


def _mock_quote(symbol: str) -> Quote:
    rng = random.Random(symbol)
    base = 50_000 + rng.randint(0, 100_000)
    change_rate = round(rng.uniform(-3.0, 3.0), 2)
    return Quote(
        symbol=symbol,
        name=_NAME_MAP.get(symbol, f"종목{symbol}"),
        price=float(base),
        change=round(base * change_rate / 100, 0),
        change_rate=change_rate,
        volume=rng.randint(100_000, 5_000_000),
        timestamp=dt.datetime.now(dt.timezone.utc),
    )


def _mock_daily_bars(symbol: str, days: int) -> list[DailyBar]:
    rng = random.Random(symbol)
    base = 50_000 + rng.randint(0, 100_000)
    bars: list[DailyBar] = []
    today = dt.date.today()
    price = float(base)
    cursor = today
    while len(bars) < days:
        cursor = cursor - dt.timedelta(days=1)
        if cursor.weekday() >= 5:
            continue
        drift = rng.uniform(-0.025, 0.025)
        new_price = max(1000.0, price * (1 + drift))
        high = max(price, new_price) * (1 + abs(rng.uniform(0, 0.012)))
        low = min(price, new_price) * (1 - abs(rng.uniform(0, 0.012)))
        bars.append(
            DailyBar(
                date=cursor,
                open=round(price, 0),
                high=round(high, 0),
                low=round(low, 0),
                close=round(new_price, 0),
                volume=rng.randint(100_000, 5_000_000),
            )
        )
        price = new_price
    bars.sort(key=lambda b: b.date)
    return bars


def _naver_main_url(symbol: str) -> str:
    return f"https://finance.naver.com/item/main.nhn?code={symbol}"


def _naver_day_url(symbol: str, page: int) -> str:
    return f"https://finance.naver.com/item/sise_day.nhn?code={symbol}&page={page}"


def _fetch_naver_html(url: str) -> str:
    resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10.0)
    resp.raise_for_status()
    return resp.text


def _naver_tables(url: str) -> list[pd.DataFrame]:
    html = _fetch_naver_html(url)
    return pd.read_html(StringIO(html), header=0)


def _naver_company_name(symbol: str) -> str | None:
    html = _fetch_naver_html(_naver_main_url(symbol))
    m = re.search(r"<title>([^<]+)</title>", html)
    if not m:
        return None
    title = m.group(1).strip()
    if ":" in title:
        title = title.split(":", 1)[0].strip()
    return title or None


def _naver_daily_page(symbol: str, page: int) -> pd.DataFrame:
    tables = _naver_tables(_naver_day_url(symbol, page))
    for table in tables:
        cols = set(str(c) for c in table.columns)
        if {"날짜", "종가", "전일비", "시가", "고가", "저가", "거래량"}.issubset(cols):
            return table
    return pd.DataFrame()


def _row_to_quote(symbol: str, row: pd.Series, name: str | None = None) -> Quote:
    close = _to_float(row["종가"])
    diff_text = str(row["전일비"])
    diff = _extract_diff(diff_text)
    prev_close = close - diff if diff_text else close
    change_rate = (diff / prev_close * 100) if prev_close else 0.0
    if "하락" in diff_text or "하향" in diff_text:
        change_rate = -abs(change_rate)
    elif "상승" in diff_text or "상향" in diff_text:
        change_rate = abs(change_rate)
    if not name:
        name = _NAME_MAP.get(symbol, f"종목{symbol}")
    return Quote(
        symbol=symbol,
        name=name,
        price=close,
        change=diff,
        change_rate=round(change_rate, 2),
        volume=int(_to_float(row["거래량"])),
        timestamp=dt.datetime.now(dt.timezone.utc),
    )


def _row_to_daily_bar(row: pd.Series) -> DailyBar:
    date = _parse_naver_date(str(row["날짜"]))
    return DailyBar(
        date=date,
        open=_to_float(row["시가"]),
        high=_to_float(row["고가"]),
        low=_to_float(row["저가"]),
        close=_to_float(row["종가"]),
        volume=int(_to_float(row["거래량"])),
    )


def _to_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^0-9.\-]", "", str(value))
    return float(text or 0)


def _extract_diff(text: str) -> float:
    amount = _to_float(text)
    if "하락" in text or "하향" in text:
        return -abs(amount)
    if "상승" in text or "상향" in text:
        return abs(amount)
    return amount


def _parse_naver_date(text: str) -> dt.date:
    cleaned = text.strip().replace("/", ".")
    candidates = ["%Y.%m.%d", "%y.%m.%d", "%m.%d"]
    for fmt in candidates:
        try:
            parsed = dt.datetime.strptime(cleaned, fmt)
            if fmt == "%m.%d":
                parsed = parsed.replace(year=dt.date.today().year)
            return parsed.date()
        except ValueError:
            continue
    raise ValueError(f"unsupported naver date format: {text}")


def _short_exc(exc: Exception) -> str:
    msg = f"{exc.__class__.__name__}: {exc}"
    return msg if len(msg) <= 180 else msg[:177] + "..."
