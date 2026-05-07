"""Optional LLM provider loading for Gemini-backed manual tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LlmSettings:
    provider: str
    model: str
    api_key_present: bool


def load_llm_settings() -> LlmSettings:
    provider = os.getenv("AI_LLM_PROVIDER", "gemini")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return LlmSettings(
        provider=provider,
        model=model,
        api_key_present=bool(os.getenv("GEMINI_API_KEY")),
    )


def create_gemini_client() -> Optional[object]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    from google import genai

    return genai.Client(api_key=api_key)
