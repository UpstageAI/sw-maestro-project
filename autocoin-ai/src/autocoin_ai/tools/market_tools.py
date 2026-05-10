"""Market data mock tools."""

from __future__ import annotations

from autocoin_ai.tools._mock_data import MOCK_VOLATILITY
from autocoin_ai.tools.registry import tool

_VOLATILITY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "symbol": {"type": "STRING"},
        "days": {"type": "INTEGER"},
    },
    "required": ["symbol", "days"],
}


@tool(_VOLATILITY_SCHEMA, "Get volatility (ATR%) for a symbol over N days.")
def get_volatility(symbol: str, days: int) -> dict:
    entry = MOCK_VOLATILITY.get(symbol.upper())
    if entry is None:
        return {"symbol": symbol.upper(), "atr_pct": 0.05, "days": days, "verdict": "normal"}
    return {"symbol": symbol.upper(), "atr_pct": entry["atr_pct"], "days": days, "verdict": entry["verdict"]}
