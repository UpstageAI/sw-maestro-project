import pytest

from newspick_ai.chat.chat_service import ChatService


class FakeEmbedder:
    def embed(self, query: str) -> list[float]:
        return [0.1, 0.2]


class FakeRetriever:
    def __init__(self, articles):
        self._articles = articles

    async def retrieve(self, vector, top_k):
        return self._articles[:top_k]


class FakeStreamer:
    async def stream(self, question, context):
        yield "token", {"text": "답변"}


@pytest.mark.asyncio
async def test_chat_done_event_contains_article_card_summary_fields():
    retrieved = [
        {"id": "a1", "title": "기사1", "source": "src1", "publishedAt": "2026-05-12T09:00:00Z", "content": "내용1", "score": 0.9},
        {"id": "a2", "title": "기사2", "source": "src2", "publishedAt": "2026-05-12T10:00:00Z", "content": "내용2", "score": 0.8},
    ]
    service = ChatService(
        embedder=FakeEmbedder(),
        retriever=FakeRetriever(retrieved),
        streamer=FakeStreamer(),
    )

    events = []
    async for event_name, data in service.stream("질문"):
        events.append((event_name, data))

    done_events = [d for n, d in events if n == "done"]
    assert len(done_events) == 1

    articles = done_events[0]["articles"]
    assert len(articles) == 2
    for article in articles:
        assert "id" in article
        assert "title" in article
        assert "source" in article
        assert "publishedAt" in article
        assert "content" not in article
        assert "score" not in article
