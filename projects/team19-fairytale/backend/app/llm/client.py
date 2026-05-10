"""LLM 추상화. LLM_PROVIDER=fake 이면 키 없이 더미 응답으로 흐름을 검증한다."""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.config import settings


class FakeChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        last = messages[-1].content if messages else ""
        text = (
            "[FAKE LLM 응답]\n"
            "제목: 따뜻한 하루의 작은 모험\n\n"
            "옛날 옛적, 호기심 많은 작은 아이가 오늘 있었던 일을 떠올렸어요. "
            "주변 친구와 가족의 도움으로 마음의 작은 매듭을 풀어가며 "
            "따뜻한 하루를 마무리했답니다.\n\n"
            "한 줄 교훈: 오늘 하루도 사랑받고 있어요.\n"
            f"\n(원본 입력 일부: {str(last)[:80]}...)"
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


DEFAULT_TIMEOUT_SEC = 30.0
DEFAULT_MAX_RETRIES = 2


def get_chat_model() -> BaseChatModel:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            temperature=0.8,
            timeout=DEFAULT_TIMEOUT_SEC,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    if provider == "solar":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=settings.solar_api_key,
            base_url=settings.solar_base_url,
            model=settings.solar_model,
            temperature=0.8,
            timeout=DEFAULT_TIMEOUT_SEC,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    return FakeChatModel()
