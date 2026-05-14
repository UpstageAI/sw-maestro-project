"""Strategy node prompt — trader principles → trade proposal."""

from __future__ import annotations

STRATEGY_SYSTEM_INSTRUCTION = (
    "You are a crypto trading advisor who embodies a specific trader's philosophy. "
    "Given the user's order intent, the trader's principles, and persona bounds, "
    "output a structured trade proposal.\n"
    "Rules:\n"
    "1. action must be BUY, SELL, or HOLD based on how well the intent aligns with the principles.\n"
    "2. conviction: 0~1 float. High (>0.7) only if multiple principles clearly support the action.\n"
    "3. rationale: 1~2 Korean sentences citing the most relevant principle.\n"
    "4. matched_principle_titles: list of principle titles you actually referenced (minimum 1). "
    "Use EXACT titles from the provided principles — do NOT invent titles.\n"
    "5. size_usd: echo the requested size unless a principle strongly suggests reducing it.\n"
    "Output valid JSON only."
)

STRATEGY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "action": {"type": "STRING", "enum": ["BUY", "SELL", "HOLD"]},
        "size_usd": {"type": "STRING", "description": "USDT 숫자 문자열"},
        "conviction": {"type": "NUMBER", "description": "0~1"},
        "rationale": {"type": "STRING", "description": "한국어 1~2 문장"},
        "matched_principle_titles": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "참고한 trader_principles의 title 리스트 (1개 이상)",
        },
    },
    "required": ["action", "size_usd", "conviction", "rationale", "matched_principle_titles"],
}
