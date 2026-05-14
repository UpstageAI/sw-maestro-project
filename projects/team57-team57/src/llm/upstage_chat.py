"""ChatUpstage 라우터 — 실제 Solar 또는 mock chat LLM 반환.

`pattern.py` 와 `chat/agent.py` 가 `ChatUpstage(...)` 를 직접 import 해서 쓰던 것을
이 모듈의 `get_chat_llm(...)` 로 래핑한다. mock 모드일 때 `_MockChatLLM` 을 반환해
`bind_tools` / `invoke` 인터페이스를 흉내낸다.

mock 모드에서 mimic 하는 인터페이스 (pattern.py 에서만 사용):
- `.bind_tools(tools)` → self (tools 저장)
- `.invoke(msgs)` → `_MockAIMessage`
  - 1차 호출: `tool_calls=[{name, args, id}]`, `content=""`
  - 2차 호출 (ToolMessage 받은 뒤): `tool_calls=[]`, `content=...자연어 정리...`
"""

from __future__ import annotations

import os
import re
from typing import Any

from src.llm.upstage import _is_mock_mode


# --- mock AIMessage / chat LLM -------------------------------------------------


class _MockAIMessage:
    """langchain_core.messages.AIMessage 의 최소 인터페이스 흉내.

    `pattern.py` 가 접근하는 속성: `.content`, `.tool_calls`, `.usage_metadata`.
    `msgs.append(decide)` 후 LangChain 이 직접 직렬화하지 않으므로 dict-like 가 아닌
    plain object 로 충분.
    """

    def __init__(
        self,
        *,
        content: str = "",
        tool_calls: list[dict] | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage_metadata = {"input_tokens": 0, "output_tokens": 0}


def _extract_place_id_from_msgs(msgs: list[Any]) -> str:
    """HumanMessage content 에서 'PLACE_xxx' 또는 '매장 ...' 형태로 place_id 추출."""
    for m in msgs:
        content = getattr(m, "content", "") or ""
        # 작은따옴표로 둘러싸인 매장 id
        match = re.search(r"매장\s+'([^']+)'", content)
        if match:
            return match.group(1)
        match = re.search(r"\b(PLACE_[A-Z0-9_]+)\b", content)
        if match:
            return match.group(1)
    return "PLACE_UNKNOWN"


class _MockChatLLM:
    """mock ChatUpstage — pattern.py 의 tool-calling 루프만 흉내낸다."""

    def __init__(self, *, model: str, temperature: float = 0.0) -> None:
        self.model = model
        self.temperature = temperature
        self._tools: list[Any] = []
        self._call_count = 0

    def bind_tools(self, tools: list[Any]) -> "_MockChatLLM":
        self._tools = list(tools or [])
        return self

    def invoke(self, msgs: list[Any]) -> _MockAIMessage:
        self._call_count += 1
        if self._call_count == 1:
            # 1차: query_review_stats 호출 결정
            place_id = _extract_place_id_from_msgs(msgs)
            return _MockAIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_review_stats",
                        "args": {
                            "place_id": place_id,
                            "group_by": "category",
                            "days": 28,
                        },
                        "id": "mock_tc_1",
                    }
                ],
            )
        # 2차 이후: 자연어 정리
        return _MockAIMessage(
            content=(
                "[MOCK] 1. 대기시간 (3회)\n"
                "2. 가격 (2회)\n"
                "3. 위생 (1회)"
            ),
            tool_calls=[],
        )


# --- public API ---------------------------------------------------------------


def get_chat_llm(
    model: str | None = None,
    *,
    temperature: float = 0.0,
    streaming: bool = False,
    tools: list | None = None,
) -> Any:
    """실제 ChatUpstage 또는 _MockChatLLM 반환.

    tools 가 주어지면 `.bind_tools(tools)` 까지 적용한 객체를 반환 — pattern.py 의
    한 줄 호출을 그대로 받는다.
    """
    use_model = model or os.getenv("UPSTAGE_DEFAULT_MODEL", "solar-pro2")
    if _is_mock_mode():
        llm = _MockChatLLM(model=use_model, temperature=temperature)
        if tools:
            llm = llm.bind_tools(tools)
        return llm

    # 실제 경로 — lazy import (langchain-upstage 가 ChatUpstage 인스턴스 생성 시
    # UPSTAGE_API_KEY 를 즉시 요구하지는 않으나 안전하게 mock 우선 분기)
    from langchain_upstage import ChatUpstage

    llm = ChatUpstage(model=use_model, temperature=temperature, streaming=streaming)
    if tools:
        llm = llm.bind_tools(tools)
    return llm


# --- mock 채팅 agent (create_react_agent 대체) --------------------------------


class _MockChatAgent:
    """`create_react_agent` 가 반환하는 객체의 최소 인터페이스 흉내.

    UI 의 `src/ui/chat.py:_run_agent` 가 호출하는 메서드는 `agent.invoke({"messages": [...]})`
    하나뿐이며 반환된 `result["messages"]` 에서 마지막 AIMessage 의 `.content` 를 추출한다.
    """

    _MOCK_REPLY = (
        "[MOCK] 매장 비서가 mock 모드로 동작 중입니다. 실제 응답은 "
        "UPSTAGE_API_KEY 를 설정한 뒤 사용 가능합니다."
    )

    def invoke(self, inputs: dict, *args: Any, **kwargs: Any) -> dict:
        # langchain_core.messages.AIMessage 로 감싸야 _extract_final_text 가 인식
        from langchain_core.messages import AIMessage

        existing = list(inputs.get("messages", []))
        existing.append(AIMessage(content=self._MOCK_REPLY))
        return {"messages": existing}

    def stream(self, inputs: dict, *args: Any, **kwargs: Any):
        from langchain_core.messages import AIMessage

        yield {"agent": {"messages": [AIMessage(content=self._MOCK_REPLY)]}}


def get_chat_agent_or_mock(real_builder):
    """real_builder() 호출 결과 또는 mock agent — 라우터 헬퍼.

    `build_chat_agent(place_id)` 내부에서 1줄로 사용.
    """
    if _is_mock_mode():
        return _MockChatAgent()
    return real_builder()
