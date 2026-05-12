from __future__ import annotations

from pathlib import Path


def test_ai_application_does_not_contain_binance_execution_calls():
    src = Path("src/autocoin_ai")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in src.rglob("*.py"))

    forbidden = [
        "testnet.binance.vision",
        "api.binance.com",
        "timestamp=",
        "BINANCE_API_KEY",
        "BINANCE_SECRET",
        "create_order",
        "newOrder",
    ]
    for token in forbidden:
        assert token not in combined
