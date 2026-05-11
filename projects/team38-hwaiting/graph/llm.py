"""Upstage Solar LLM 어댑터 (PRD §7.3 / m-2).

- 1차: `langchain-upstage` 의 `ChatUpstage`
- 백업: `langchain-openai` 의 `ChatOpenAI(base_url="https://api.upstage.ai/v1/solar")`

OQ-9 (JSON 모드 지원 여부) 가 미해결이므로 호출자는 `json_mode=True` 를 요청해도
시스템 프롬프트로 JSON 강제 + Pydantic 검증을 함께 사용해야 한다.
"""
from __future__ import annotations

import os
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

UPSTAGE_BASE_URL = "https://api.upstage.ai/v1/solar"
DEFAULT_TIMEOUT = 60


def _model_name(role: Literal["primary", "fast"]) -> str:
    if role == "fast":
        return os.getenv("UPSTAGE_MODEL_FAST", "solar-1-mini-chat")
    return os.getenv("UPSTAGE_MODEL_PRIMARY", "solar-pro")


def make_llm(
    role: Literal["primary", "fast"] = "primary",
    json_mode: bool = False,
    temperature: float = 0.2,
) -> BaseChatModel:
    """Upstage Solar 클라이언트 — 공식 SDK 우선, 미설치 시 OpenAI 호환 폴백."""
    api_key = os.getenv("UPSTAGE_API_KEY", "")
    model = _model_name(role)

    llm: BaseChatModel
    try:
        from langchain_upstage import ChatUpstage  # type: ignore

        llm = ChatUpstage(
            api_key=api_key,
            model=model,
            temperature=temperature,
            timeout=DEFAULT_TIMEOUT,
        )
    except ImportError:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            api_key=api_key,
            base_url=UPSTAGE_BASE_URL,
            model=model,
            temperature=temperature,
            timeout=DEFAULT_TIMEOUT,
        )

    if json_mode:
        try:
            return llm.bind(response_format={"type": "json_object"})  # type: ignore[return-value]
        except Exception:
            return llm
    return llm


def invoke_with_retry(
    llm: BaseChatModel,
    messages: list[BaseMessage],
    *,
    max_attempts: int = 2,
) -> Any:
    """1회 재시도 — 호출자가 응답 검증 후 재호출 책임을 가지므로 단순 래퍼."""
    last_err: Exception | None = None
    for _ in range(max_attempts):
        try:
            return llm.invoke(messages)
        except Exception as e:  # noqa: BLE001
            last_err = e
    if last_err is not None:
        raise last_err
    raise RuntimeError("LLM invocation failed without exception")
