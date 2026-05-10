"""Intake node prompt — NL → structured order intent."""

from __future__ import annotations

INTAKE_SYSTEM_INSTRUCTION = (
    "You are a crypto trading assistant that parses Korean/English natural language "
    "order requests into structured JSON. "
    "Rules:\n"
    "1. Extract symbol (e.g. BTCUSDT), side (BUY/SELL), type (MARKET/LIMIT), "
    "size_usd (USDT string). If KRW amount mentioned, convert at 1 USD = 1350 KRW.\n"
    "2. Infer trader_id from mention of '워뇨띠'/'wonyotti', 'BNF'/'bnf', "
    "'매억남'/'maeoaknam', '리버모어'/'livermore'. "
    "Leave empty string if not mentioned.\n"
    "3. Infer inferred_persona from words like '공격적/aggressive' (AGGRESSIVE), "
    "'보수적/conservative' (CONSERVATIVE), '중립/moderate' (MODERATE). Default MODERATE.\n"
    "4. Set persona_override_reason if persona was explicitly stated in text, else empty string.\n"
    "5. Set ambiguity_score: 0=fully clear, 1=very ambiguous. "
    "Score > 0.5 if symbol is unclear, size is missing, or intent is contradictory.\n"
    "Output valid JSON only."
)

INTAKE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "symbol": {"type": "STRING"},
        "side": {"type": "STRING", "enum": ["BUY", "SELL"]},
        "type": {"type": "STRING", "enum": ["MARKET", "LIMIT"]},
        "size_usd": {
            "type": "STRING",
            "description": "USDT 숫자 문자열. KRW 발화면 1 USD ≈ 1350 KRW로 환산",
        },
        "trader_id": {
            "type": "STRING",
            "description": "발화 추론 결과. 미명시 시 빈 문자열",
        },
        "inferred_persona": {
            "type": "STRING",
            "enum": ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"],
        },
        "persona_override_reason": {
            "type": "STRING",
            "description": "발화에 명시 시 사유, 없으면 빈 문자열",
        },
        "ambiguity_score": {
            "type": "NUMBER",
            "description": "0=명확, 1=모호. 0.5 초과면 HOLD",
        },
    },
    "required": [
        "symbol",
        "side",
        "type",
        "size_usd",
        "trader_id",
        "inferred_persona",
        "persona_override_reason",
        "ambiguity_score",
    ],
}
