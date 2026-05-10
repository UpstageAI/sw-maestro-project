"""Policy-related mock tools."""

from __future__ import annotations

from autocoin_ai.tools._mock_data import MOCK_DAILY_LOSS
from autocoin_ai.tools.registry import tool

_PERSONA_BOUNDS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "action": {"type": "STRING"},
        "symbol": {"type": "STRING"},
        "size_usd": {"type": "STRING"},
    },
    "required": ["action", "symbol", "size_usd"],
}

_DAILY_LOSS_SCHEMA = {
    "type": "OBJECT",
    "properties": {},
    "required": [],
}


@tool(_PERSONA_BOUNDS_SCHEMA, "Check if proposed action is within persona bounds.")
def check_persona_bounds(action: str, symbol: str, size_usd: str) -> dict:
    try:
        size = float(size_usd)
    except (ValueError, TypeError):
        return {"verdict": "error", "reason": "invalid size_usd"}
    if size > 2000:
        return {"verdict": "warn", "reason": "size_usd exceeds MODERATE max_order_usd"}
    return {"verdict": "ok", "action": action, "symbol": symbol, "size_usd": size_usd}


@tool(_DAILY_LOSS_SCHEMA, "Check daily loss limit status (placeholder for Phase 3c).")
def check_daily_loss_limit() -> dict:
    return dict(MOCK_DAILY_LOSS)
