from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class UpstageClient:
    _instance: Optional[UpstageClient] = None
    _client: Optional[AsyncOpenAI] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.upstage_api_key,
                base_url="https://api.upstage.ai/v1",
            )
        return self._client

    async def _retry(self, fn, max_attempts: int = 3):
        for attempt in range(max_attempts):
            try:
                return await fn()
            except Exception:
                logger.exception("Upstage API 호출 실패 (attempt %s/%s)", attempt + 1, max_attempts)
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))

    async def get_embedding(self, text: str, model: str = "embedding-query") -> list[float]:
        truncated_text = text[:4000]

        async def _call():
            response = await self.client.embeddings.create(model=model, input=truncated_text)
            return response.data[0].embedding

        return await self._retry(_call)

    async def get_chat_completion(
        self,
        messages: list[dict],
        model: str = "solar-1-mini-chat",
        response_format: Optional[dict] = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if settings.mock_mode:
            return json.dumps({
                "candidates": [
                    {
                        "mentor_id": i,
                        "rank": i,
                        "extracted_facts": f"테스트용 추출 팩트 {i}입니다.",
                        "reasoning_process": f"테스트용 사고 과정 {i}입니다.",
                        "reason": f"테스트용 적합 이유 {i}입니다.",
                        "weak_point": f"테스트용 아쉬운 점 {i}입니다.",
                    }
                    for i in range(1, 6)
                ]
            })

        async def _call():
            kwargs = {"model": model, "messages": messages}
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if response_format:
                kwargs["response_format"] = response_format
            elif "json" in str(messages).lower():
                kwargs["response_format"] = {"type": "json_object"}
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

        return await self._retry(_call)

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "solar-pro",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        return await self.get_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )


upstage_client = UpstageClient()
