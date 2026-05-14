"""Account-related mock tools."""

from __future__ import annotations

from autocoin_ai.tools._mock_data import MOCK_BALANCE, MOCK_CONCENTRATION
from autocoin_ai.tools.registry import tool

_BALANCE_SCHEMA = {
    "type": "OBJECT",
    "properties": {"asset": {"type": "STRING"}},
    "required": ["asset"],
}

_CONCENTRATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "symbol": {"type": "STRING"},
        "proposed_size_usd": {"type": "STRING"},
    },
    "required": ["symbol", "proposed_size_usd"],
}


@tool(_BALANCE_SCHEMA, "Get account balance for an asset from Binance Spot Testnet.")
def get_balance(asset: str) -> dict:
    entry = MOCK_BALANCE.get(asset.upper())
    if entry is None:
        return {"asset": asset.upper(), "free": "0.0", "locked": "0.0"}
    return dict(entry)


@tool(_CONCENTRATION_SCHEMA, "Get concentration risk for a proposed position.")
def get_concentration_risk(symbol: str, proposed_size_usd: str) -> dict:
    entry = MOCK_CONCENTRATION.get(symbol.upper())
    if entry is None:
        return {"symbol": symbol.upper(), "concentration_pct": 0.0, "verdict": "ok"}
    return dict(entry)
