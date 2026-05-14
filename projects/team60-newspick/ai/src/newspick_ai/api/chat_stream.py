import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


async def get_chat_service():
    from newspick_ai.chat.chat_service import ChatService

    return ChatService()


def create_chat_stream_router() -> APIRouter:
    router = APIRouter()

    @router.post("/chat-stream")
    async def chat_stream(request: ChatRequest, service=Depends(get_chat_service)):
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="message must not be blank")
        return StreamingResponse(
            _sse_stream(service, request.message),
            media_type="text/event-stream",
        )

    return router


async def _sse_stream(service, message: str) -> AsyncIterator[str]:
    try:
        async for event_name, data in service.stream(message):
            yield _format_sse(event_name, data)
    except Exception as exc:
        yield _format_sse("error", {"message": str(exc)})


def _format_sse(event_name: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_name}\ndata: {payload}\n\n"
