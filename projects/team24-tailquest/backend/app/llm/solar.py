"""Solar API wrapper.

Uses the OpenAI-compatible endpoint at https://api.upstage.ai/v1/solar so we get
streaming, async, retries, and Pydantic structured output via openai SDK.

We intentionally don't pull in langchain-upstage here — the openai SDK gives us
the same capability with one less dependency layer. langchain-upstage will be
used later for RAG retrievers (Phase 2) where it adds real value.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Awaitable, Callable, TypeVar

import time

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.log_format import stage

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.upstage_api_key or "missing-key",
        base_url="https://api.upstage.ai/v1/solar",
    )


async def structured_chat(
    response_model: type[T],
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.3,
    reasoning_effort: str | None = "medium",
) -> T:
    """Call Solar with a Pydantic schema and parse the response into it.

    Solar Pro 3 advertises 100% schema compliance but we still treat the call as
    fallible — the caller decides what to do on failure (retry, fall back).
    """
    settings = get_settings()
    client = get_client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    extra: dict = {}
    chosen = model or settings.solar_model
    if reasoning_effort and chosen.startswith("solar-pro3"):
        extra["reasoning_effort"] = reasoning_effort

    stage(
        "📡 [SOLAR] structured_chat",
        schema=response_model.__name__,
        model=chosen,
        temp=temperature,
    )
    t0 = time.monotonic()
    completion = await client.beta.chat.completions.parse(
        model=chosen,
        messages=messages,  # type: ignore[arg-type]
        response_format=response_model,
        temperature=temperature,
        **extra,
    )
    elapsed = time.monotonic() - t0
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        stage(
            "✗ [SOLAR] empty parse",
            schema=response_model.__name__,
            elapsed=f"{elapsed:.2f}s",
        )
        raise RuntimeError(
            f"Solar returned no parsed content for {response_model.__name__}: "
            f"{completion.choices[0].message.content!r}"
        )
    stage(
        "⏱  [SOLAR] done",
        schema=response_model.__name__,
        elapsed=f"{elapsed:.2f}s",
    )
    return parsed


async def tool_calling_chat(
    *,
    system: str,
    user: str,
    tools: list[dict],
    tool_dispatcher: Callable[[str, dict], Awaitable[str]],
    model: str | None = None,
    temperature: float = 0.5,
    max_iters: int = 2,
) -> list[dict]:
    """Run a multi-turn tool-calling loop with Solar.

    On each iteration:
      1. Call Solar with the current `messages` and `tools=...`.
      2. If the assistant emits tool_calls, run them via `tool_dispatcher`,
         append the tool result(s) to `messages`, and loop again.
      3. If no tool_calls, return the final `messages` list.

    `max_iters` caps the number of tool-roundtrips (each iter = 1 LLM call +
    optional N tool dispatches). The caller can then feed `messages` back into
    `structured_chat_after_tools(...)` to coerce a Pydantic schema.
    """
    settings = get_settings()
    client = get_client()
    chosen = model or settings.solar_model

    # Solar-pro3 with tool_choice="auto" tends to ignore the tool list and answer
    # from internal knowledge. A short system-level reminder of which tools are
    # available — and *when* they should be used — measurably increases tool_call
    # rates without breaking schema-bound second-leg parses.
    tool_hint = ""
    if tools:
        tool_lines = []
        for t in tools:
            fn = t.get("function", {}) if isinstance(t, dict) else {}
            name = fn.get("name", "?")
            desc = fn.get("description", "")
            tool_lines.append(f"- {name}: {desc}")
        tool_hint = (
            "\n\n[사용 가능한 도구]\n"
            + "\n".join(tool_lines)
            + "\n\n시의성 있는 정보·외부 사실 확인·최신 변경 사항이 필요한 질문이라고 판단되면 "
              "위 도구를 호출하세요. 충분한 사전 지식만으로 답할 수 있는 일반 개념은 호출하지 마세요."
        )

    user_with_hint = user
    if tools:
        user_with_hint = user + (
            "\n\n[참고: 사용 가능한 도구]\n"
            "위 정보 중 시의성(예: 라이브러리 새 버전·최근 변경)·구체 사실 확인·"
            "키워드에 등장하는 외부 자료 등을 먼저 검증해야 한다고 판단되면, "
            "최종 답을 만들기 전에 web_search 도구를 호출하세요. 일반 개념(예: TCP, 프로세스)은 호출하지 마세요."
        )

    messages: list[dict] = [
        {"role": "system", "content": system + tool_hint},
        {"role": "user", "content": user_with_hint},
    ]
    stage(
        "📡 [SOLAR] tool_calling start",
        model=chosen,
        max_iters=max_iters,
        tools=[t.get("function", {}).get("name", "?") for t in tools],
    )
    t_total = time.monotonic()
    for iteration in range(max_iters):
        try:
            completion = await client.chat.completions.create(
                model=chosen,
                messages=messages,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type]
                tool_choice="auto",
                temperature=temperature,
            )
        except Exception as exc:
            logger.warning("tool_calling_chat: completion failed (iter=%d): %s", iteration, exc)
            break

        msg = completion.choices[0].message
        msg_payload: dict = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            logger.warning(
                "tool_calling_chat: iter=%d fired %d tool_call(s): %s",
                iteration,
                len(msg.tool_calls),
                [tc.function.name for tc in msg.tool_calls],
            )
            msg_payload["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(msg_payload)

        if not msg.tool_calls:
            if iteration == 0:
                logger.warning("tool_calling_chat: no tool_call fired — model answered directly.")
            stage(
                "⏱  [SOLAR] tool_calling done",
                iters=iteration + 1,
                elapsed=f"{time.monotonic() - t_total:.2f}s",
                used_tool=False,
            )
            return messages  # nothing more to do

        # Dispatch each tool_call sequentially, appending tool results.
        for tc in msg.tool_calls:
            raw_args = tc.function.arguments or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            try:
                result = await tool_dispatcher(tc.function.name, args)
            except Exception as exc:
                logger.warning("tool_dispatcher failed for %s: %s", tc.function.name, exc)
                result = f"도구 호출 중 오류: {exc}"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    stage(
        "⏱  [SOLAR] tool_calling done",
        iters=max_iters,
        elapsed=f"{time.monotonic() - t_total:.2f}s",
        used_tool=True,
    )
    return messages


async def structured_chat_after_tools(
    response_model: type[T],
    *,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    reasoning_effort: str | None = "medium",
) -> T:
    """Force a Pydantic-typed answer from an existing tool-calling conversation.

    Pass the `messages` returned by `tool_calling_chat(...)` to coerce the
    assistant's final answer into `response_model`. This is the "second leg" of
    the two-step tool-calling pattern (loop → schema).
    """
    settings = get_settings()
    client = get_client()
    chosen = model or settings.solar_model
    extra: dict = {}
    if reasoning_effort and chosen.startswith("solar-pro3"):
        extra["reasoning_effort"] = reasoning_effort

    stage(
        "📡 [SOLAR] structured_after_tools",
        schema=response_model.__name__,
        model=chosen,
        msg_count=len(messages),
    )
    t0 = time.monotonic()
    completion = await client.beta.chat.completions.parse(
        model=chosen,
        messages=messages,  # type: ignore[arg-type]
        response_format=response_model,
        temperature=temperature,
        **extra,
    )
    elapsed = time.monotonic() - t0
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        stage(
            "✗ [SOLAR] empty parse",
            schema=response_model.__name__,
            elapsed=f"{elapsed:.2f}s",
        )
        raise RuntimeError(
            f"Solar returned no parsed content for {response_model.__name__}: "
            f"{completion.choices[0].message.content!r}"
        )
    stage(
        "⏱  [SOLAR] structured_after_tools done",
        schema=response_model.__name__,
        elapsed=f"{elapsed:.2f}s",
    )
    return parsed
