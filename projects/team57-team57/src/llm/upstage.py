"""Upstage Solar API wrapper — UPSTAGE_API_KEY 기반 LLM 호출.

Solar API 는 OpenAI Chat Completions 호환이라 표준 `openai` SDK 의 base_url 만
변경해서 사용. structured output 은 `response_format={"type": "json_schema", ...}`
로 schema 강제. tool calling 은 langchain-upstage `ChatUpstage.bind_tools(...)` 로
별도 처리 (pattern.py 에서).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

load_dotenv()

DEFAULT_MODEL = os.getenv("UPSTAGE_DEFAULT_MODEL", "solar-pro2")
UPSTAGE_BASE_URL = os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1")

PREVIEW_MAX = 200


class UpstageError(RuntimeError):
    """Upstage API 호출 실패."""


# --- mock 모드 라우팅 ---------------------------------------------------------


def _is_mock_mode() -> bool:
    """`REVIEW_OPS_LLM=mock` 또는 `UPSTAGE_API_KEY` 미설정 시 mock 라우팅."""
    if os.getenv("REVIEW_OPS_LLM", "").lower() == "mock":
        return True
    return not os.getenv("UPSTAGE_API_KEY")


# --- 클라이언트 (process-wide singleton) -------------------------------------


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise UpstageError(
                "UPSTAGE_API_KEY 가 설정되지 않았습니다.\n"
                "  1) cp .env.example .env\n"
                "  2) https://console.upstage.ai 에서 API 키 발급 후 .env 에 입력"
            )
        _client = OpenAI(api_key=api_key, base_url=UPSTAGE_BASE_URL)
    return _client


# --- helpers ------------------------------------------------------------------


def _truncate(s: str, n: int = PREVIEW_MAX) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "…"


def _extract_meta(
    completion: ChatCompletion,
    *,
    system: str,
    prompt: str,
    response_text: str,
    model: str,
    duration_ms: int,
) -> dict:
    """trace 용 메타 dict — cli.py 와 키 호환."""
    usage = completion.usage
    return {
        "model": model,
        "duration_ms": duration_ms,
        "duration_api_ms": duration_ms,  # subprocess 분리 없으므로 동일
        "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
        # Solar 는 prompt caching 미지원 (현재). 0으로 표기.
        "cache_read_tokens": 0,
        "cache_create_tokens": 0,
        "system_preview": _truncate(system),
        "prompt_preview": _truncate(prompt),
        "response_preview": _truncate(response_text),
    }


def _do_call(
    *,
    system: str,
    prompt: str,
    model: str,
    response_format: dict | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> tuple[ChatCompletion, int]:
    """Solar API 호출. (completion, duration_ms) 반환."""
    client = _get_client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    t0 = time.perf_counter()
    try:
        completion = client.chat.completions.create(**kwargs)
    except Exception as e:  # noqa: BLE001
        raise UpstageError(f"Solar API 호출 실패: {e}") from e
    duration_ms = int((time.perf_counter() - t0) * 1000)
    return completion, duration_ms


# --- public API: with meta ----------------------------------------------------


def complete_text_with_meta(
    prompt: str, *, system: str, model: str | None = None
) -> tuple[str, dict]:
    """Plain text completion + 메타 (drafter / diff hint / pattern.summarize)."""
    if _is_mock_mode():
        from src.llm import upstage_mock
        return upstage_mock.complete_text_with_meta(prompt, system=system, model=model)
    use_model = model or DEFAULT_MODEL
    completion, duration_ms = _do_call(system=system, prompt=prompt, model=use_model)
    text = (completion.choices[0].message.content or "").strip()
    meta = _extract_meta(
        completion,
        system=system,
        prompt=prompt,
        response_text=text,
        model=use_model,
        duration_ms=duration_ms,
    )
    return text, meta


def complete_json_with_meta(
    prompt: str,
    *,
    system: str,
    schema: dict,
    model: str | None = None,
) -> tuple[dict, dict]:
    """Structured output via response_format = json_schema (classifier / checklist).

    Solar 는 OpenAI 호환이라 `{"type": "json_schema", "json_schema": {"name", "schema", "strict"}}`
    형태로 schema 강제 가능.
    """
    if _is_mock_mode():
        from src.llm import upstage_mock
        return upstage_mock.complete_json_with_meta(
            prompt, system=system, schema=schema, model=model
        )
    use_model = model or DEFAULT_MODEL
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "structured_output",
            "schema": schema,
            "strict": True,
        },
    }
    completion, duration_ms = _do_call(
        system=system,
        prompt=prompt,
        model=use_model,
        response_format=response_format,
    )
    raw = completion.choices[0].message.content or "{}"
    try:
        structured = json.loads(raw)
    except json.JSONDecodeError as e:
        raise UpstageError(
            f"structured_output 파싱 실패: {e}\nraw head: {raw[:300]}"
        ) from e
    meta = _extract_meta(
        completion,
        system=system,
        prompt=prompt,
        response_text=raw,
        model=use_model,
        duration_ms=duration_ms,
    )
    return structured, meta


# --- legacy wrappers ---------------------------------------------------------


def complete_text(prompt: str, *, system: str, model: str | None = None) -> str:
    text, _ = complete_text_with_meta(prompt, system=system, model=model)
    return text


def complete_json(
    prompt: str,
    *,
    system: str,
    schema: dict,
    model: str | None = None,
) -> dict:
    structured, _ = complete_json_with_meta(prompt, system=system, schema=schema, model=model)
    return structured
