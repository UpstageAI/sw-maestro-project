import pytest

from newspick_ai.graph.config import CATEGORY_FEEDS
from newspick_ai.graph.refresh_graph import build_collect_all_node


class FakeCollector:
    def __init__(self):
        self.calls = []

    def run(
        self,
        state,
        feed_url: str,
        category: str,
        source_name: str | None = None,
    ):
        self.calls.append((feed_url, category, source_name))
        return state


@pytest.mark.asyncio
async def test_collect_node_collects_only_selected_category_feeds():
    collector = FakeCollector()
    collect = build_collect_all_node(collector)

    await collect({"articles": [], "events": [], "categoryIds": ["tech"]})

    assert collector.calls == [
        (source["url"], "테크", source["source"])
        for source in CATEGORY_FEEDS["tech"]["feeds"]
    ]


def test_category_feeds_use_multiple_publishers_per_category():
    assert all(len(feed["feeds"]) >= 2 for feed in CATEGORY_FEEDS.values())
    assert any(
        "rss.etnews.com" in source["url"]
        for source in CATEGORY_FEEDS["tech"]["feeds"]
    )
    assert any(
        "mk.co.kr" in source["url"]
        for source in CATEGORY_FEEDS["economy"]["feeds"]
    )
    assert any(
        "newsis.com" in source["url"]
        for source in CATEGORY_FEEDS["policy"]["feeds"]
    )


def test_category_feeds_keep_publisher_name_separate_from_category_label():
    for feed in CATEGORY_FEEDS.values():
        for source in feed["feeds"]:
            assert source["source"] != feed["label"]
