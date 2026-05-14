"""Persona profile definitions."""

from __future__ import annotations

from autocoin_ai.constants import PERSONA_AGGRESSIVE, PERSONA_CONSERVATIVE, PERSONA_MODERATE

PERSONA_PROFILES: dict[str, dict] = {
    PERSONA_CONSERVATIVE: {
        "max_order_usd": 500.0,
        "min_conviction": 0.75,
        "allowed_symbols": ["BTCUSDT", "ETHUSDT"],
        "required_tools": ["get_balance", "get_volatility", "check_persona_bounds"],
        "label": "보수적",
    },
    PERSONA_MODERATE: {
        "max_order_usd": 2000.0,
        "min_conviction": 0.65,
        "allowed_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        "required_tools": ["get_balance", "get_volatility"],
        "label": "중립적",
    },
    PERSONA_AGGRESSIVE: {
        "max_order_usd": 10000.0,
        "min_conviction": 0.50,
        "allowed_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        "required_tools": ["get_balance"],
        "label": "공격적",
    },
}
