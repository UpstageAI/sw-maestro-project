from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from models.schema import PriceRecord, PriceStats

VOLUME_SPIKE_MULTIPLIER = 2.0
ABNORMAL_MOVE_THRESHOLD = 5.0  # %


def fetch_price_data(
    ticker: str, start_date: str, end_date: str
) -> tuple[list[PriceRecord], PriceStats, str, str, str]:
    """주가·거래량 조회. (prices, stats, company_name, sector, industry) 반환."""
    info = yf.Ticker(ticker).info
    company_name: str = info.get("longName") or info.get("shortName") or ticker
    sector: str = info.get("sector") or ""
    industry: str = info.get("industry") or ""

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_exclusive = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    # Fetch 35 extra days before start to get: (1) a reference close for period_pct_change,
    # (2) a 30-day historical avg volume baseline — avoids 0% when range has only 1 trading day.
    history_start = (start_dt - timedelta(days=35)).strftime("%Y-%m-%d")
    df_all = yf.download(ticker, start=history_start, end=end_exclusive, progress=False, auto_adjust=True)
    if df_all.empty:
        raise ValueError(f"주가 데이터 없음: {ticker} ({start_date} ~ {end_date})")

    df_all = df_all.copy()
    df_all.columns = [c[0] if isinstance(c, tuple) else c for c in df_all.columns]
    df_all = df_all.dropna(subset=["Close"])

    start_ts = pd.Timestamp(start_date)
    df_before = df_all[df_all.index < start_ts]
    df = df_all[df_all.index >= start_ts]

    if df.empty:
        raise ValueError(f"주가 데이터 없음: {ticker} ({start_date} ~ {end_date})")

    # Reference close: last trading day strictly before start_date (for accurate period_pct_change)
    reference_close = float(df_before["Close"].iloc[-1]) if not df_before.empty else float(df["Close"].iloc[0])

    # 30-day historical avg volume as baseline for spike detection and volume change
    hist_avg_vol = float(df_before["Volume"].mean()) if not df_before.empty else float(df["Volume"].mean())

    df["pct_change"] = df["Close"].pct_change() * 100

    spike_dates = [
        d.strftime("%Y-%m-%d")
        for d, v in zip(df.index, df["Volume"])
        if v >= hist_avg_vol * VOLUME_SPIKE_MULTIPLIER
    ]

    records: list[PriceRecord] = []
    for idx, row in df.iterrows():
        records.append(
            PriceRecord(
                date=idx.date(),
                open=round(float(row["Open"]), 4),
                high=round(float(row["High"]), 4),
                low=round(float(row["Low"]), 4),
                close=round(float(row["Close"]), 4),
                volume=int(row["Volume"]),
                pct_change=round(float(row["pct_change"]) if not pd.isna(row["pct_change"]) else 0.0, 4),
            )
        )

    last_close = float(df["Close"].iloc[-1])
    period_pct = round((last_close - reference_close) / reference_close * 100, 2)

    daily_changes = df["pct_change"].dropna()
    stats = PriceStats(
        period_pct_change=period_pct,
        max_single_day_gain=round(float(daily_changes.max()), 2) if not daily_changes.empty else period_pct,
        max_single_day_loss=round(float(daily_changes.min()), 2) if not daily_changes.empty else period_pct,
        avg_volume=round(hist_avg_vol, 0),
        volume_spike_dates=spike_dates,
        is_abnormal_move=bool(daily_changes.abs().max() >= ABNORMAL_MOVE_THRESHOLD) if not daily_changes.empty else abs(period_pct) >= ABNORMAL_MOVE_THRESHOLD,
    )

    return records, stats, company_name, sector, industry
