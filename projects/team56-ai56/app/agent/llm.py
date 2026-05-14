from __future__ import annotations

import requests

from app.config import get_settings


class UpstageChat:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.upstage_api_key
        self.model = settings.upstage_model
        self.base_url = settings.upstage_base_url

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        timeout: int = 30,
    ) -> str:
        if not self.available():
            raise RuntimeError("Upstage API key is not configured")
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
