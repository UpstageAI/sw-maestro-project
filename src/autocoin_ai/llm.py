"""Gemini LLM client — structured output and function calling."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(frozen=True)
class LlmSettings:
    provider: str
    model: str
    api_key_present: bool


def load_llm_settings() -> LlmSettings:
    provider = os.getenv("AI_LLM_PROVIDER", "gemini")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    return LlmSettings(
        provider=provider,
        model=model,
        api_key_present=bool(os.getenv("GEMINI_API_KEY")),
    )


_client: Optional[Any] = None


def create_gemini_client() -> Optional[Any]:
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    from google import genai

    _client = genai.Client(api_key=api_key)
    return _client


def _get_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-pro")


def gemini_generate(
    prompt: str,
    response_schema: dict,
    system_instruction: str = "",
) -> dict:
    from google.genai import types

    client = create_gemini_client()
    if client is None:
        raise RuntimeError("GEMINI_API_KEY not set")

    resp = client.models.generate_content(
        model=_get_model(),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0,
        ),
    )
    return resp.parsed  # type: ignore[return-value]


@dataclass
class StepResult:
    is_final: bool
    function_calls: List[Any]
    text: str
    candidate_content: Any


def gemini_step_with_tools(
    contents: List[Any],
    tools: List[Any],
    system_instruction: str = "",
) -> StepResult:
    from google.genai import types

    client = create_gemini_client()
    if client is None:
        raise RuntimeError("GEMINI_API_KEY not set")

    resp = client.models.generate_content(
        model=_get_model(),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            tools=tools,
            temperature=0,
        ),
    )
    candidate = resp.candidates[0]
    parts = candidate.content.parts or []
    fcs = [p.function_call for p in parts if getattr(p, "function_call", None)]
    text = "".join(p.text for p in parts if getattr(p, "text", None))
    return StepResult(
        is_final=not fcs,
        function_calls=fcs,
        text=text,
        candidate_content=candidate.content,
    )
