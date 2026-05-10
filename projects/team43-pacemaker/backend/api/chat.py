"""/agent/chat SSE 라우터. B(박장우) ↔ C(이유준) 합의로 구현.

라우터는 얇게: run_agent_stream가 yield하는 ChatChunk를 그대로 SSE data 프레임으로 흘려보낸다.
payload 스키마는 schemas/CLAUDE.md 표 참조.
"""
from collections.abc import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from agent.graph import run_agent_stream
from schemas.models import ChatChunk, ChatRequest

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    """ChatChunk(JSON) 시퀀스를 SSE로 스트리밍.

    type ∈ {"text", "tool_call", "proposal", "done", "error"}.
    각 이벤트는 `data: <ChatChunk JSON>\\n\\n` 형식.
    """

    async def event_source() -> AsyncIterator[dict[str, str]]:
        try:
            async for chunk in run_agent_stream(
                request.message, thread_id=request.thread_id
            ):
                yield {"data": chunk.model_dump_json()}
        except Exception as exc:  # 그래프가 직접 ChatChunk(error)를 emit하면 여기 안 옴
            err = ChatChunk(type="error", payload={"message": str(exc)})
            yield {"data": err.model_dump_json()}

    return EventSourceResponse(event_source())
