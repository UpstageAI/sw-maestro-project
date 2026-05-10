"""Mock data for tool calls — Binance Spot Testnet simulation."""

from __future__ import annotations

MOCK_BALANCE: dict[str, dict] = {
    "USDT": {"asset": "USDT", "free": "5000.0", "locked": "0.0"},
    "BTC": {"asset": "BTC", "free": "0.05", "locked": "0.0"},
    "ETH": {"asset": "ETH", "free": "1.5", "locked": "0.0"},
    "BNB": {"asset": "BNB", "free": "10.0", "locked": "0.0"},
}

MOCK_VOLATILITY: dict[str, dict] = {
    "BTCUSDT": {"symbol": "BTCUSDT", "atr_pct": 0.045, "days": 7, "verdict": "normal"},
    "ETHUSDT": {"symbol": "ETHUSDT", "atr_pct": 0.055, "days": 7, "verdict": "normal"},
    "DOGEUSDT": {"symbol": "DOGEUSDT", "atr_pct": 0.120, "days": 7, "verdict": "high"},
    "BNBUSDT": {"symbol": "BNBUSDT", "atr_pct": 0.038, "days": 7, "verdict": "normal"},
}

MOCK_CONCENTRATION: dict[str, dict] = {
    "BTCUSDT": {"symbol": "BTCUSDT", "concentration_pct": 0.10, "verdict": "ok"},
    "ETHUSDT": {"symbol": "ETHUSDT", "concentration_pct": 0.08, "verdict": "ok"},
    "DOGEUSDT": {"symbol": "DOGEUSDT", "concentration_pct": 0.25, "verdict": "high"},
    "BNBUSDT": {"symbol": "BNBUSDT", "concentration_pct": 0.06, "verdict": "ok"},
}

ALLOWED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "BNBUSDT"}

MOCK_DAILY_LOSS = {"loss_usd": "0.0", "limit_usd": "500.0", "verdict": "ok"}
