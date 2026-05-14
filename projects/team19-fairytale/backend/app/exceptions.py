"""
AI 모듈에서 외부로 던지는 도메인 예외.

권장 매핑:
    StoryGenerationError  → 422 Unprocessable Entity
    LLMUnavailableError   → 503 Service Unavailable
    StoryParsingError     → 502 Bad Gateway (업스트림 응답 불량)
"""

from __future__ import annotations


class StoryGenerationError(Exception):
    """동화 생성 과정 전반의 실패 (포괄 베이스)."""

    def __init__(self, message: str, *, stage: str | None = None):
        super().__init__(message)
        self.stage = stage      # "plan" | "write" | "critique" | "finalize" | None

    def __str__(self) -> str:
        base = super().__str__()
        return f"[{self.stage}] {base}" if self.stage else base


class LLMUnavailableError(StoryGenerationError):
    """LLM 호출 자체가 실패 (타임아웃·5xx·인증·rate-limit 등)."""


class StoryParsingError(StoryGenerationError):
    """LLM 응답을 파싱할 수 없어 결과물을 만들 수 없는 경우."""
