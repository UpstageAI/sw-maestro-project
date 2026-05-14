import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from newspick_ai.api.refresh_stream import (
    create_graph_refresh_runner,
    create_refresh_stream_router,
)


class FakeGraph:
    async def ainvoke(self, state):
        assert state == {"articles": [], "events": []}
        return {
            "articles": [],
            "events": [],
            "persistedArticleIds": [
                "article_001",
                "article_002",
                "article_001",
            ],
        }


@pytest.mark.asyncio
async def test_refresh_stream_done_event_contains_persisted_article_ids():
    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(
            refresh_runner=create_graph_refresh_runner(FakeGraph())
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/refresh-stream")

    done_event = next(
        event for event in response.text.split("\n\n") if event.startswith("event: done")
    )
    payload = json.loads(done_event.split("data: ", 1)[1])

    assert "event: done" in response.text
    assert payload["articleIds"] == ["article_001", "article_002"]
    assert len(payload["articleIds"]) == len(set(payload["articleIds"]))
