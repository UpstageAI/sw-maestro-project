import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from newspick_ai.api.refresh_stream import (
    create_graph_refresh_runner,
    create_refresh_stream_router,
)


class FakeReportGenerator:
    def __init__(self):
        self.received_article_ids = None

    async def generate(self, article_ids: list[str]) -> dict:
        self.received_article_ids = article_ids
        return {"date": "2026-05-12", "report_id": "report_20260512"}


class FakeGraph:
    async def ainvoke(self, state):
        self.received_state = state
        return {
            "articles": [],
            "events": [],
            "persistedArticleIds": ["article_001", "article_002"],
        }


@pytest.mark.asyncio
async def test_refresh_graph_done_event_contains_report_date():
    fake_generator = FakeReportGenerator()
    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(
            refresh_runner=create_graph_refresh_runner(
                FakeGraph(),
                report_generator=fake_generator,
            )
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

    assert payload["reportDate"] == "2026-05-12"
    assert "articleIds" in payload
    assert fake_generator.received_article_ids == ["article_001", "article_002"]


@pytest.mark.asyncio
async def test_refresh_graph_runner_passes_category_ids_to_graph():
    fake_graph = FakeGraph()
    events = [
        event
        async for event in create_graph_refresh_runner(fake_graph)(["tech"], None)
    ]

    assert fake_graph.received_state["categoryIds"] == ["tech"]
    assert events[-1][0] == "done"
