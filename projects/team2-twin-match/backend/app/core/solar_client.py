"""Async client for Upstage Solar LLM.

Solar exposes an OpenAI-compatible Chat Completions endpoint, so we reuse the
official `openai` SDK and override `base_url` + `api_key`. All LLM calls in the
project should go through this module so model/provider swaps stay isolated.
"""

import asyncio
from typing import Any, Dict, List, Optional

from openai import APIError, AsyncOpenAI, RateLimitError

from app.core.config import config
from app.core.errors.error import SolarAPIException
from app.core.logger import logger


_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    """Lazy singleton — avoids constructing the HTTP client at import time."""
    global _client
    if _client is None:
        if not config.UPSTAGE_API_KEY:
            raise SolarAPIException(
                "UPSTAGE_API_KEY 가 설정되지 않았습니다. .env 를 확인하세요."
            )
        _client = AsyncOpenAI(
            api_key=config.UPSTAGE_API_KEY,
            base_url=config.UPSTAGE_BASE_URL,
        )
    return _client


async def chat_completion(
    system_prompt: str,
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
    retries: int = 1,
) -> str:
    """Send a chat completion request to Solar and return the assistant text.

    Args:
        system_prompt: System message content (Agent persona / Matchmaker rules).
        messages: Prior turns formatted as `{"role": "user"|"assistant", "content": str}`.
        model: Override `SOLAR_MODEL` from config.
        temperature / max_tokens: Override defaults from config.
        response_format: e.g. `{"type": "json_object"}` for Matchmaker analysis.
        extra: Extra kwargs forwarded to `chat.completions.create`.
        retries: Additional attempts after the first failure (default 1).

    Raises:
        SolarAPIException: Wraps any underlying provider error.
    """
    client = get_client()
    payload: Dict[str, Any] = {
        "model": model or config.SOLAR_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + list(messages),
        "temperature": (
            temperature if temperature is not None else config.SOLAR_TEMPERATURE
        ),
        "max_tokens": max_tokens if max_tokens is not None else config.SOLAR_MAX_TOKENS,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    if extra:
        payload.update(extra)

    attempt = 0
    last_err: Optional[Exception] = None
    while attempt <= retries:
        try:
            resp = await client.chat.completions.create(**payload)
            return (resp.choices[0].message.content or "").strip()
        except RateLimitError as e:
            last_err = e
            logger.warning("Solar rate limit (attempt %s): %s", attempt + 1, e)
            await asyncio.sleep(2)
        except APIError as e:
            last_err = e
            logger.warning("Solar API error (attempt %s): %s", attempt + 1, e)
        except Exception as e:  # network, timeout, etc.
            last_err = e
            logger.warning("Solar unexpected error (attempt %s): %s", attempt + 1, e)
        attempt += 1

    raise SolarAPIException(f"Solar LLM API 호출 실패: {last_err}")
