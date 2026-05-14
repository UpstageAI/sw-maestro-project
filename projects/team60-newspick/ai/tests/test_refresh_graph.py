import pytest

from newspick_ai.graph.refresh_graph import build_refresh_graph
from newspick_ai.graph.state import RefreshState


@pytest.mark.asyncio
async def test_refresh_graph_runs_collector_node_and_returns_state():
    async def fake_collector(state: RefreshState) -> RefreshState:
        return {
            "articles": [
                {
                    "id": "article_001",
                    "url": "https://example.com/a1",
                    "title": "첫 기사",
                }
            ],
            "events": [
                *state["events"],
                {
                    "stage": "collect",
                    "message": "1건 수집",
                    "articleIds": ["article_001"],
                },
            ],
        }

    graph = build_refresh_graph(collector=fake_collector)

    output = await graph.ainvoke({"articles": [], "events": []})

    assert output["articles"][0]["id"] == "article_001"
    assert output["events"][0]["stage"] == "collect"
