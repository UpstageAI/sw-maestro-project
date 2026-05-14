import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from newspick_ai.api.chat_stream import create_chat_stream_router, get_chat_service


class FakeChatService:
    async def stream(self, message: str):
        yield "token", {"text": "안녕"}
        yield "token", {"text": "하세요"}
        yield "done", {"articles": []}


@pytest.mark.asyncio
async def test_chat_stream_endpoint_emits_token_and_done_events():
    app = FastAPI()
    app.include_router(create_chat_stream_router())
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/chat-stream", json={"message": "오늘 뉴스"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert response.text.count("event: token") == 2
    assert response.text.count("event: done") == 1


@pytest.mark.asyncio
async def test_chat_stream_blank_message_returns_400():
    app = FastAPI()
    app.include_router(create_chat_stream_router())
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/chat-stream", json={"message": "  "})

    assert response.status_code == 400
