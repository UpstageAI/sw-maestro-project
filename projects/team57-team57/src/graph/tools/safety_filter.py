"""Risky phrase post-filter — defense in depth alongside prompt guidance.

NEVER promise refunds, discounts, free items, or legal admissions in an
LLM-generated reply. This dictionary catches LLM slip-ups deterministically.

prompt-level guidance + post-filter 의 이중 안전망 구조이며,
치환된 사실은 반드시 trace (`safety_notes`) 에 노출되어 사장님이 인지 가능해야 한다.
"""
from __future__ import annotations

# 절대 약속하면 안 되는 표현 → 중립 대체어.
# 키 순서가 곧 적용 순서이므로, 더 긴 phrase 를 먼저 두어야 부분 치환 사고를 막는다.
RISKY_PHRASES: dict[str, str] = {
    "전액 환불": "개별 안내",
    "100% 환불": "개별 안내",
    "전액 보상": "개별 안내",
    "보상해드리겠습니다": "확인 후 안내드리겠습니다",
    "할인 쿠폰": "별도 안내",
    "무료 제공": "별도 안내",
    "법적 책임": "(검토)",
    "법적 조치": "(검토)",
    "환불": "별도 안내",
    "할인": "별도 안내",
    "공짜": "별도 안내",
    "고소": "(검토)",
}


def filter_risky_phrases(reply: str) -> tuple[str, list[str]]:
    """답글에서 위험 표현을 안전 표현으로 치환.

    Returns:
        (filtered_reply, notes) — notes 는 사용자에게 노출되는 사람 친화적 한 줄 문구.
    """
    notes: list[str] = []
    out = reply or ""
    for phrase, replacement in RISKY_PHRASES.items():
        if phrase in out:
            out = out.replace(phrase, replacement)
            notes.append(f"'{phrase}' → '{replacement}'")
    return out, notes
