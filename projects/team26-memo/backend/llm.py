"""LLM 프로바이더 추상화.

지원:
  - offline (기본, API 키 불필요, 휴리스틱 기반)
  - openai (gpt-4o-mini 등)
  - gemini (gemini-1.5-flash 등)
  - anthropic (claude-3-5-haiku 등)
  - upstage (solar-pro 등, https://console.upstage.ai/docs/agents)

환경변수:
  LLM_PROVIDER  : 사용할 프로바이더 (기본 offline)
  OPENAI_API_KEY / OPENAI_MODEL
  GEMINI_API_KEY / GEMINI_MODEL
  ANTHROPIC_API_KEY / ANTHROPIC_MODEL
  UPSTAGE_API_KEY / UPSTAGE_MODEL

LLM 호출이 실패하거나 JSON 파싱이 실패하면 자동으로 offline 결과로
폴백한다. 이 폴백은 데모/운영 환경에서 백엔드가 절대 500을 내지 않도록
안전망 역할을 한다.
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .extractor import (
    ExtractedAction,
    extract_action_items,
    extract_summary,
    find_missed_agenda,
    suggest_next_agenda,
)
from .prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 공통
# ---------------------------------------------------------------------------


def _coerce_response(payload: Any) -> Dict[str, Any]:
    """LLM 응답을 안전한 dict 로 정규화."""
    if not isinstance(payload, dict):
        return {"summary": "", "missed_agenda": "", "next_agenda": "", "action_items": []}

    def _as_str(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, list):
            return "\n".join(str(x) for x in v if x)
        return str(v)

    def _coerce_sub_items(value: Any) -> List[Dict[str, str]]:
        if not isinstance(value, list):
            return []
        sub_items: List[Dict[str, str]] = []
        for sub in value:
            if isinstance(sub, dict):
                who = _as_str(sub.get("who")).strip()
                when = _as_str(sub.get("when")).strip()
                what = _as_str(sub.get("what")).strip()
                if who or when or what:
                    sub_items.append({"who": who, "when": when, "what": what})
            elif isinstance(sub, str) and sub.strip():
                sub_items.append({"who": "", "when": "", "what": sub.strip()})
        return sub_items

    items_raw = payload.get("action_items") or []
    items: List[Dict[str, Any]] = []
    if isinstance(items_raw, list):
        for it in items_raw:
            if isinstance(it, dict):
                title = _as_str(it.get("title")).strip()
                who = _as_str(it.get("who")).strip()
                when = _as_str(it.get("when")).strip()
                what = _as_str(it.get("what")).strip()
                sub_items = _coerce_sub_items(it.get("sub_items") or it.get("children"))
                if title or who or when or what or sub_items:
                    items.append(
                        {
                            "title": title,
                            "who": who,
                            "when": when,
                            "what": what,
                            "sub_items": sub_items,
                        }
                    )
            elif isinstance(it, str) and it.strip():
                items.append(
                    {
                        "title": it.strip(),
                        "who": "",
                        "when": "",
                        "what": it.strip(),
                        "sub_items": [],
                    }
                )

    return {
        "summary": _as_str(payload.get("summary")).strip(),
        "missed_agenda": _as_str(payload.get("missed_agenda")).strip(),
        "next_agenda": _as_str(payload.get("next_agenda")).strip(),
        "action_items": items,
    }


def _extract_json_block(text: str) -> Optional[str]:
    """LLM 응답에서 JSON 블록만 골라낸다 (코드 펜스, 부가 텍스트 제거)."""
    if not text:
        return None
    # 코드 펜스 안의 JSON
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fence:
        return fence.group(1)
    # 첫 '{' ~ 마지막 '}' 까지를 시도
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


def _parse_llm_json(text: str) -> Optional[Dict[str, Any]]:
    block = _extract_json_block(text)
    if not block:
        return None
    try:
        return json.loads(block)
    except json.JSONDecodeError:
        # 흔한 깨짐: trailing comma, 단일 인용부호 → 간단 보정
        cleaned = re.sub(r",\s*([}\]])", r"\1", block)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


# ---------------------------------------------------------------------------
# 베이스
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def analyze(self, agenda: str, transcript: str) -> Dict[str, Any]:
        """반드시 _coerce_response 형태의 dict 를 반환."""


# ---------------------------------------------------------------------------
# Offline (휴리스틱) - 기본값
# ---------------------------------------------------------------------------


class OfflineProvider(LLMProvider):
    name = "offline"

    def analyze(self, agenda: str, transcript: str) -> Dict[str, Any]:
        actions: List[ExtractedAction] = extract_action_items(transcript)
        missed = find_missed_agenda(agenda, transcript)
        nxt = suggest_next_agenda(agenda, transcript, missed, actions)
        summary = extract_summary(transcript)

        return _coerce_response(
            {
                "summary": summary or "회의 내용을 충분히 추출하지 못했습니다.",
                "missed_agenda": "\n".join(f"{i+1}. {m}" for i, m in enumerate(missed)),
                "next_agenda": "\n".join(f"{i+1}. {n}" for i, n in enumerate(nxt)),
                "action_items": [
                    {
                        "title": a.what[:60],
                        "who": a.who,
                        "when": a.when,
                        "what": a.what,
                        "sub_items": [],
                    }
                    for a in actions
                ],
            }
        )


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI  # 지연 import

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def analyze(self, agenda: str, transcript: str) -> Dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(agenda, transcript)},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        parsed = _parse_llm_json(text)
        if parsed is None:
            raise ValueError("OpenAI 응답에서 JSON을 파싱하지 못했습니다.")
        return _coerce_response(parsed)


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        import google.generativeai as genai  # 지연 import

        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model

    def analyze(self, agenda: str, transcript: str) -> Dict[str, Any]:
        model = self._genai.GenerativeModel(
            self._model_name,
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )
        result = model.generate_content(build_user_prompt(agenda, transcript))
        text = (result.text or "").strip()
        parsed = _parse_llm_json(text)
        if parsed is None:
            raise ValueError("Gemini 응답에서 JSON을 파싱하지 못했습니다.")
        return _coerce_response(parsed)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-latest") -> None:
        import anthropic  # 지연 import

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def analyze(self, agenda: str, transcript: str) -> Dict[str, Any]:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_prompt(agenda, transcript)}],
        )
        text = "".join(block.text for block in msg.content if hasattr(block, "text"))
        parsed = _parse_llm_json(text)
        if parsed is None:
            raise ValueError("Anthropic 응답에서 JSON을 파싱하지 못했습니다.")
        return _coerce_response(parsed)


# ---------------------------------------------------------------------------
# Upstage (Solar Agent API — OpenAI-compatible, https://api.upstage.ai/v1)
# ---------------------------------------------------------------------------


class UpstageProvider(LLMProvider):
    name = "upstage"

    def __init__(self, api_key: str, model: str = "solar-pro") -> None:
        from openai import OpenAI  # 지연 import — openai SDK로 Upstage 호환 엔드포인트 사용

        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.upstage.ai/v1",
        )
        self._model = model

    def analyze(self, agenda: str, transcript: str) -> Dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(agenda, transcript)},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        parsed = _parse_llm_json(text)
        if parsed is None:
            raise ValueError("Upstage 응답에서 JSON을 파싱하지 못했습니다.")
        return _coerce_response(parsed)


# ---------------------------------------------------------------------------
# 팩토리 / 폴백 래퍼
# ---------------------------------------------------------------------------


class FallbackProvider(LLMProvider):
    """기본 프로바이더 호출이 실패하면 offline 으로 폴백."""

    def __init__(self, primary: LLMProvider) -> None:
        self._primary = primary
        self._offline = OfflineProvider()
        self.name = f"{primary.name}+offline-fallback"

    def analyze(self, agenda: str, transcript: str) -> Dict[str, Any]:
        try:
            return self._primary.analyze(agenda, transcript)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM(%s) 호출 실패, offline 폴백: %s", self._primary.name, exc)
            result = self._offline.analyze(agenda, transcript)
            # 디버그 신호 (프론트는 무시)
            result["_fallback"] = True  # type: ignore[index]
            result["_fallback_reason"] = str(exc)  # type: ignore[index]
            return result


def build_primary_provider() -> LLMProvider:
    """MainAgent와 함께 사용. FallbackProvider 래핑 없이 원시 프로바이더 반환.

    MainAgent가 재시도/폴백을 직접 담당하므로 FallbackProvider가 필요 없다.
    """
    selected = (os.getenv("LLM_PROVIDER") or "offline").strip().lower()

    if selected == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            logger.warning("OPENAI_API_KEY 미설정 - offline 으로 강등")
            return OfflineProvider()
        try:
            return OpenAIProvider(key, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAI 초기화 실패, offline 으로 강등: %s", exc)
            return OfflineProvider()

    if selected == "gemini":
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            logger.warning("GEMINI_API_KEY 미설정 - offline 으로 강등")
            return OfflineProvider()
        try:
            return GeminiProvider(key, os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini 초기화 실패, offline 으로 강등: %s", exc)
            return OfflineProvider()

    if selected == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            logger.warning("ANTHROPIC_API_KEY 미설정 - offline 으로 강등")
            return OfflineProvider()
        try:
            return AnthropicProvider(
                key, os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Anthropic 초기화 실패, offline 으로 강등: %s", exc)
            return OfflineProvider()

    if selected == "upstage":
        key = os.getenv("UPSTAGE_API_KEY", "").strip()
        if not key:
            logger.warning("UPSTAGE_API_KEY 미설정 - offline 으로 강등")
            return OfflineProvider()
        try:
            return UpstageProvider(key, os.getenv("UPSTAGE_MODEL", "solar-pro"))
        except Exception as exc:  # noqa: BLE001
            logger.error("Upstage 초기화 실패, offline 으로 강등: %s", exc)
            return OfflineProvider()


    return OfflineProvider()


def build_provider() -> LLMProvider:
    """환경변수 기반으로 LLMProvider 생성."""
    selected = (os.getenv("LLM_PROVIDER") or "offline").strip().lower()

    if selected == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            logger.warning("OPENAI_API_KEY 미설정 - offline 으로 강등")
            return OfflineProvider()
        try:
            primary = OpenAIProvider(key, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
            return FallbackProvider(primary)
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAI 초기화 실패, offline 으로 강등: %s", exc)
            return OfflineProvider()

    if selected == "gemini":
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            logger.warning("GEMINI_API_KEY 미설정 - offline 으로 강등")
            return OfflineProvider()
        try:
            primary = GeminiProvider(key, os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
            return FallbackProvider(primary)
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini 초기화 실패, offline 으로 강등: %s", exc)
            return OfflineProvider()

    if selected == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            logger.warning("ANTHROPIC_API_KEY 미설정 - offline 으로 강등")
            return OfflineProvider()
        try:
            primary = AnthropicProvider(
                key, os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
            )
            return FallbackProvider(primary)
        except Exception as exc:  # noqa: BLE001
            logger.error("Anthropic 초기화 실패, offline 으로 강등: %s", exc)
            return OfflineProvider()

    if selected == "upstage":
        key = os.getenv("UPSTAGE_API_KEY", "").strip()
        if not key:
            logger.warning("UPSTAGE_API_KEY 미설정 - offline 으로 강등")
            return OfflineProvider()
        try:
            primary = UpstageProvider(key, os.getenv("UPSTAGE_MODEL", "solar-pro"))
            return FallbackProvider(primary)
        except Exception as exc:  # noqa: BLE001
            logger.error("Upstage 초기화 실패, offline 으로 강등: %s", exc)
            return OfflineProvider()

    return OfflineProvider()
