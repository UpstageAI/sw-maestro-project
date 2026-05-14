from __future__ import annotations

import yfinance as yf

from models.schema import BenchmarkComparison

SECTOR_ETF_MAP: dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}

INDUSTRY_PEERS_MAP: dict[str, list[str]] = {
    # Technology
    "Semiconductors":                   ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "MU", "TSM"],
    "Consumer Electronics":             ["AAPL", "SONY", "HPQ", "DELL"],
    "Software - Infrastructure":        ["MSFT", "ORCL", "IBM", "CSCO"],
    "Software - Application":           ["CRM", "ADBE", "NOW", "INTU"],
    "Electronic Components":            ["TEL", "APH", "GLW", "TDY"],
    # Communication Services
    "Internet Content & Information":   ["GOOGL", "META", "SNAP", "PINS"],
    "Entertainment":                    ["NFLX", "DIS", "WBD", "PARA"],
    "Telecom Services":                 ["VZ", "T", "TMUS"],
    # Financials
    "Banks - Diversified":              ["JPM", "BAC", "WFC", "C", "GS", "MS"],
    "Asset Management":                 ["BLK", "SCHW", "MS", "GS"],
    "Insurance - Diversified":          ["BRK-B", "MET", "PRU", "AFL"],
    # Consumer Discretionary
    "Auto Manufacturers":               ["TSLA", "GM", "F", "TM", "HMC"],
    "Internet Retail":                  ["AMZN", "BABA", "EBAY", "ETSY"],
    "Specialty Retail":                 ["HD", "LOW", "TGT", "COST"],
    "Restaurants":                      ["MCD", "SBUX", "YUM", "CMG"],
    # Consumer Staples
    "Beverages - Non-Alcoholic":        ["KO", "PEP", "MNST", "CELH"],
    "Household & Personal Products":    ["PG", "CL", "KMB", "CHD"],
    "Grocery Stores":                   ["WMT", "COST", "KR", "SFM"],
    # Healthcare
    "Drug Manufacturers - General":     ["JNJ", "PFE", "ABBV", "MRK", "LLY"],
    "Biotechnology":                    ["AMGN", "GILD", "BIIB", "REGN", "VRTX"],
    "Health Information Services":      ["UNH", "CVS", "CI", "HUM"],
    "Medical Devices":                  ["MDT", "ABT", "SYK", "BSX"],
    # Energy
    "Oil & Gas Integrated":             ["XOM", "CVX", "BP", "SHEL"],
    "Oil & Gas E&P":                    ["COP", "EOG", "DVN", "PXD"],
    # Industrials
    "Aerospace & Defense":              ["BA", "LMT", "RTX", "NOC", "GD"],
    "Industrial Conglomerates":         ["GE", "HON", "MMM"],
    "Trucking":                         ["UPS", "FDX", "XPO"],
    # Materials
    "Specialty Chemicals":              ["LIN", "APD", "SHW", "ECL"],
    "Gold":                             ["NEM", "GOLD", "AEM", "KGC"],
    # Real Estate
    "REIT - Industrial":                ["PLD", "DRE", "EGP"],
    "REIT - Specialty":                 ["AMT", "CCI", "EQIX", "DLR"],
    # Utilities
    "Utilities - Regulated Electric":   ["NEE", "DUK", "SO", "D", "AEP"],
}

SECTOR_PEERS_MAP: dict[str, list[str]] = {
    "Technology":               ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "Healthcare":               ["JNJ", "UNH", "PFE", "ABBV", "MRK"],
    "Financial Services":       ["JPM", "BAC", "WFC", "GS", "MS"],
    "Consumer Cyclical":        ["AMZN", "TSLA", "HD", "NKE", "MCD"],
    "Consumer Defensive":       ["PG", "KO", "PEP", "WMT", "COST"],
    "Energy":                   ["XOM", "CVX", "COP", "EOG", "SLB"],
    "Industrials":              ["GE", "HON", "CAT", "UPS", "BA"],
    "Basic Materials":          ["LIN", "APD", "SHW", "FCX", "NEM"],
    "Real Estate":              ["PLD", "AMT", "EQIX", "SPG", "DLR"],
    "Utilities":                ["NEE", "DUK", "SO", "D", "AEP"],
    "Communication Services":   ["GOOGL", "META", "NFLX", "DIS", "CMCSA"],
}

MAX_PEERS = 3


def fetch_benchmark_data(
    ticker: str, sector: str, start_date: str, end_date: str, industry: str = ""
) -> tuple[list[BenchmarkComparison], list[str], list[str]]:
    """S&P500, 섹터 ETF, Peer 기업 수익률 비교. (benchmarks, peer_tickers, warnings) 반환."""
    import pandas as pd
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_exclusive = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    history_start = (start_dt - timedelta(days=10)).strftime("%Y-%m-%d")
    start_ts = pd.Timestamp(start_date)

    targets: list[tuple[str, str]] = [("^GSPC", "S&P 500")]

    etf = SECTOR_ETF_MAP.get(sector)
    if etf:
        targets.append((etf, f"{sector} ETF ({etf})"))

    # industry 단위 peer 우선, 없으면 sector 단위로 폴백
    peer_pool = INDUSTRY_PEERS_MAP.get(industry) or SECTOR_PEERS_MAP.get(sector, [])
    raw_peers = [t for t in peer_pool if t.upper() != ticker.upper()]
    peer_tickers = raw_peers[:MAX_PEERS]
    for p in peer_tickers:
        targets.append((p, p))

    benchmarks: list[BenchmarkComparison] = []
    warnings: list[str] = []
    for sym, label in targets:
        try:
            df = yf.download(sym, start=history_start, end=end_exclusive, progress=False, auto_adjust=True)
            if df.empty:
                warnings.append(f"벤치마크 데이터 없음: {sym}")
                continue
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df_before = df[df.index < start_ts]
            df_in = df[df.index >= start_ts]
            if df_in.empty:
                warnings.append(f"벤치마크 데이터 없음: {sym}")
                continue
            first = float(df_before["Close"].iloc[-1]) if not df_before.empty else float(df_in["Close"].iloc[0])
            last = float(df_in["Close"].iloc[-1])
            pct = round((last - first) / first * 100, 2)
            benchmarks.append(BenchmarkComparison(ticker=sym, label=label, pct_change_period=pct))
        except Exception as e:
            warnings.append(f"벤치마크 수집 실패 ({sym}): {e}")
            continue

    return benchmarks, peer_tickers, warnings
