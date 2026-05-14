from __future__ import annotations

import statistics
from typing import Any

from ..store import Chunk, store
from ..stocks import StockNotFoundError, get_stock_snapshot


def collect(symbol: str) -> dict[str, Any]:
    """종목 데이터를 수집하고 청킹하여 store에 적재."""
    store.reset(symbol)
    stock = get_stock_snapshot(symbol, include_bars=True)

    chunks: list[Chunk] = [
        Chunk(
            symbol=symbol,
            kind="quote",
            text=(
                f"{stock['name']}({symbol}) 현재가 {stock['price']:,.0f}원, "
                f"전일 대비 {stock['change_rate']:+.2f}%, 거래량 {stock['volume']:,}주."
            ),
            meta={
                "price": stock["price"],
                "change_rate": stock["change_rate"],
                "volume": stock["volume"],
            },
        )
    ]

    bars = stock.get("bars", [])
    if bars:
        closes = [float(b["close"]) for b in bars]
        first, last = closes[0], closes[-1]
        period_return = (last / first - 1) * 100 if first else 0.0
        mean_close = statistics.mean(closes) or 1.0
        vol = statistics.pstdev(closes) / mean_close * 100
        hi = max(float(b["high"]) for b in bars)
        lo = min(float(b["low"]) for b in bars)
        chunks.append(
            Chunk(
                symbol=symbol,
                kind="summary",
                text=(
                    f"{stock['name']}({symbol}) 최근 {len(bars)}거래일 종가 추이: "
                    f"시작 {first:,.0f}원 → 종료 {last:,.0f}원 ({period_return:+.2f}%), "
                    f"기간 고점 {hi:,.0f}원 / 저점 {lo:,.0f}원, "
                    f"종가 변동성(σ/μ) {vol:.2f}%."
                ),
                meta={
                    "period_return_pct": period_return,
                    "volatility_pct": vol,
                    "high": hi,
                    "low": lo,
                    "n_bars": len(bars),
                },
            )
        )
        for b in bars[-20:]:
            chunks.append(
                Chunk(
                    symbol=symbol,
                    kind="daily",
                    text=(
                        f"{b['date']} 시 {b['open']:,.0f} 고 {b['high']:,.0f} "
                        f"저 {b['low']:,.0f} 종 {b['close']:,.0f} 거래량 {b['volume']:,}"
                    ),
                    meta={"date": b["date"], "close": b["close"]},
                )
            )

    store.add_many(chunks)
    return {
        "symbol": symbol,
        "name": stock["name"],
        "price": stock["price"],
        "change": stock["change"],
        "change_rate": stock["change_rate"],
        "volume": stock["volume"],
        "market": stock.get("market", ""),
        "timestamp": stock.get("timestamp") or stock.get("updatedAt") or "",
        "n_chunks": len(chunks),
        "data_mode": stock.get("data_mode", "mock"),
        "data_source": stock.get("data_source", stock.get("data_mode", "mock")),
        "fetch_status": stock.get("fetch_status", {}),
        "fallback_reason": stock.get("fallback_reason", ""),
        "kis_auth_mode": stock.get("kis_auth_mode", "mock"),
        "kis_auth_ready": stock.get("kis_auth_ready", False),
        "bars": bars,
    }

