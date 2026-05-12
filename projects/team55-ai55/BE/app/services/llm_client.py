from __future__ import annotations

import json
import os
import asyncio
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from app.services.metrics import record_llm_raw_response


def load_local_env(path: str | Path | None = None) -> None:
    candidates = [Path(path)] if path is not None else [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


load_local_env()

UPSTAGE_BASE_URL = os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1")
UPSTAGE_MODEL = os.getenv("UPSTAGE_MODEL", "solar-mini")


@dataclass
class LlmResult:
    content: str
    tokens: int = 0


class UpstageClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = UPSTAGE_BASE_URL,
        model: str = UPSTAGE_MODEL,
        timeout: float = 4.0,
        daily_budget: int | None = None,
        max_concurrency: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = api_key or os.getenv("UPSTAGE_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.daily_budget = int(os.getenv("LLM_DAILY_BUDGET", "500")) if daily_budget is None else daily_budget
        self._budget_day = date.today()
        self._calls_today = 0
        self._semaphore = asyncio.Semaphore(max_concurrency or int(os.getenv("LLM_MAX_CONCURRENCY", "5")))
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def chat_json(
        self,
        *,
        system: str,
        user: str,
        purpose: str = "unspecified",
        temperature: float = 0,
        max_tokens: int = 800,
    ) -> dict[str, Any] | None:
        if not self.configured:
            return None
        if not self._consume_budget():
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = None
        async with self._semaphore:
            for attempt in range(2):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
                        response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                        response.raise_for_status()
                        body = response.json()
                        record_llm_raw_response(purpose, body)
                    break
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 400 and "response_format" in payload:
                        payload.pop("response_format", None)
                        continue
                    if attempt == 1:
                        return None
                except (httpx.HTTPError, ValueError):
                    if attempt == 1:
                        return None
        if body is None:
            return None

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None

    async def health(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "base_url": self.base_url,
            "model": self.model,
            "daily_budget": self.daily_budget,
            "calls_today": self._calls_today,
        }

    def _consume_budget(self) -> bool:
        today = date.today()
        if today != self._budget_day:
            self._budget_day = today
            self._calls_today = 0
        if self.daily_budget <= 0 or self._calls_today >= self.daily_budget:
            return False
        self._calls_today += 1
        return True


llm_client = UpstageClient()
