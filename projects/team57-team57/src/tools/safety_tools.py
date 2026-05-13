from __future__ import annotations

import re

PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?82[- ]?)?0\d{1,2}[- ]?\d{3,4}[- ]?\d{4}(?!\d)")
EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
LONG_DIGIT_PATTERN = re.compile(r"(?<!\d)\d{6,}(?!\d)")

RISKY_PHRASES = (
    "환불",
    "할인",
    "법적 책임",
    "전액 보상",
    "무료 제공",
    "보상해드리겠습니다",
)


def mask_personal_information(text: str) -> str:
    masked = PHONE_PATTERN.sub("[PHONE_MASKED]", text)
    masked = EMAIL_PATTERN.sub("[EMAIL_MASKED]", masked)
    masked = LONG_DIGIT_PATTERN.sub("[NUMBER_MASKED]", masked)
    return masked


def contains_korean(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def filter_risky_reply_phrases(reply: str) -> tuple[str, list[str]]:
    filtered = reply
    notes: list[str] = []

    for phrase in RISKY_PHRASES:
        if phrase in filtered:
            filtered = filtered.replace(phrase, "별도 안내")
            notes.append(f"removed risky phrase: {phrase}")

    return filtered, notes


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
