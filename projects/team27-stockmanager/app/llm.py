from __future__ import annotations

from openai import OpenAI

from .config import settings


class LLM:
    """Upstage Solar 래퍼. UPSTAGE_API_KEY가 없으면 stub 응답으로 폴백."""

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        if settings.upstage_api_key:
            try:
                self._client = OpenAI(
                    api_key=settings.upstage_api_key,
                    base_url=settings.upstage_api_base,
                )
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def generate(self, system: str, user: str) -> str:
        if not self._client:
            return _stub_response(system, user)

        try:
            resp = self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            content = resp.choices[0].message.content if resp.choices else ""
            return content or _stub_response(system, user)
        except Exception as e:
            return f"[LLM 호출 실패: {e}]\n\n" + _stub_response(system, user)


def _stub_response(system: str, user: str) -> str:
    return (
        "[LLM 미연결 - 스텁 응답]\n"
        "UPSTAGE_API_KEY가 설정되지 않아 임시 응답을 반환합니다.\n\n"
        f"system: {system[:200].strip()}\n"
        f"user: {user[:400].strip()}"
    )


llm = LLM()
