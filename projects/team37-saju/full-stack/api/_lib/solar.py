"""Solar API (Upstage) chat client — Python port of ``server/solar.ts``.

Uses the OpenAI-compatible ``/v1/chat/completions`` endpoint. Same retry
semantics as the TypeScript original: ``call_solar_json`` strips a markdown
code fence and falls back to a stricter retry when JSON parsing fails.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, TypedDict

import httpx

SOLAR_BASE_URL = os.environ.get("SOLAR_BASE_URL", "https://api.upstage.ai/v1")
DEFAULT_SOLAR_MODEL = os.environ.get("SOLAR_MODEL", "solar-pro2")


class ChatMessage(TypedDict):
    role: str  # 'system' | 'user' | 'assistant'
    content: str


class SolarOptions(TypedDict, total=False):
    api_key: str
    model: Optional[str]
    temperature: float
    max_tokens: int
    response_format: str  # 'text' | 'json_object'


class SolarApiError(Exception):
    def __init__(self, message: str, status: int = 0, body_text: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body_text = body_text


_CODE_FENCE_OPEN = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_CODE_FENCE_CLOSE = re.compile(r"```\s*$", re.IGNORECASE)


def _strip_code_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```"):
        no_open = _CODE_FENCE_OPEN.sub("", trimmed)
        no_close = _CODE_FENCE_CLOSE.sub("", no_open)
        return no_close.strip()
    return trimmed


async def call_solar(messages: List[ChatMessage], opts: SolarOptions) -> str:
    api_key = (opts.get("api_key") or "").strip()
    if not api_key:
        raise SolarApiError("Solar API key is missing", 401)

    body: Dict[str, Any] = {
        "model": opts.get("model") or DEFAULT_SOLAR_MODEL,
        "messages": messages,
        "temperature": opts.get("temperature", 0.3),
        "max_tokens": opts.get("max_tokens", 1024),
        "stream": False,
    }
    if opts.get("response_format") == "json_object":
        body["response_format"] = {"type": "json_object"}

    url = f"{SOLAR_BASE_URL.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json=body,
            )
    except httpx.HTTPError as err:
        raise SolarApiError(f"Network error contacting Solar: {err}", 0) from err

    if res.status_code >= 400:
        text = ""
        try:
            text = res.text
        except Exception:
            pass
        raise SolarApiError(
            f"Solar API error {res.status_code}: {text[:200]}",
            res.status_code,
            text,
        )

    try:
        data = res.json()
    except json.JSONDecodeError as err:
        raise SolarApiError("Solar returned non-JSON response", 500) from err

    content = ""
    choices = data.get("choices") if isinstance(data, dict) else None
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict):
            content = msg.get("content") or ""

    if not isinstance(content, str) or len(content) == 0:
        raise SolarApiError("Solar returned empty content", 500)

    return content


async def call_solar_json(messages: List[ChatMessage], opts: SolarOptions) -> Any:
    """Call Solar and parse the response as JSON, retrying once on parse failure
    by repeating with a stricter system reminder.
    """
    json_opts: SolarOptions = {**opts, "response_format": "json_object"}
    raw = await call_solar(messages, json_opts)
    cleaned = _strip_code_fence(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    retry_messages: List[ChatMessage] = [
        *messages,
        {"role": "assistant", "content": raw},
        {
            "role": "user",
            "content": (
                "Previous response was not valid JSON. Reply with ONLY a single "
                "JSON object, no prose, no markdown."
            ),
        },
    ]
    retry_opts: SolarOptions = {**json_opts, "temperature": 0.0}
    retry_raw = await call_solar(retry_messages, retry_opts)
    return json.loads(_strip_code_fence(retry_raw))
