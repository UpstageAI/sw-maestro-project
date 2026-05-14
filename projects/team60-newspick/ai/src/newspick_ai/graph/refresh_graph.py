from collections.abc import Callable
from typing import Awaitable

from langgraph.graph import END, StateGraph

from newspick_ai.graph.collector import RssCollector
from newspick_ai.graph.config import CATEGORY_FEEDS
from newspick_ai.graph.state import RefreshState


CollectorNode = Callable[[RefreshState], RefreshState | Awaitable[RefreshState]]


async def empty_collector(state: RefreshState) -> RefreshState:
    return state


def build_collect_all_node(collector: RssCollector) -> CollectorNode:
    async def collect_all(state: RefreshState) -> RefreshState:
        category_ids = state.get("categoryIds") or list(CATEGORY_FEEDS.keys())
        for category_id in category_ids:
            feed = CATEGORY_FEEDS[category_id]
            for source in feed["feeds"]:
                state = collector.run(
                    state,
                    feed_url=source["url"],
                    category=feed["label"],
                    source_name=source["source"],
                )
        return state

    return collect_all


def build_refresh_graph(collector: CollectorNode = empty_collector):
    graph = StateGraph(RefreshState)
    graph.add_node("collect", collector)
    graph.set_entry_point("collect")
    graph.add_edge("collect", END)
    return graph.compile()


def _filter_extracted(state: RefreshState) -> RefreshState:
    articles = [a for a in state["articles"] if "content" in a]
    return {**state, "articles": articles}


def build_full_refresh_graph(
    collector_node: CollectorNode,
    deduplicator,
    extractor,
    summarizer,
    validator,
    persistor,
    article_updater,
    embedder,
    quiz_generator,
    quiz_persistor,
):
    graph = StateGraph(RefreshState)
    graph.add_node("collect", collector_node)
    graph.add_node("deduplicate", deduplicator.run)
    graph.add_node("extract", extractor.run)
    graph.add_node("filter_extracted", _filter_extracted)
    graph.add_node("summarize", summarizer.run)
    graph.add_node("validate", validator.run)
    graph.add_node("persist", persistor.run)
    graph.add_node("update_article", article_updater.run)
    graph.add_node("embed", embedder.run)
    graph.add_node("generate_quiz", quiz_generator.run)
    graph.add_node("persist_quiz", quiz_persistor.run)

    graph.set_entry_point("collect")
    graph.add_edge("collect", "deduplicate")
    graph.add_edge("deduplicate", "extract")
    graph.add_edge("extract", "filter_extracted")
    graph.add_edge("filter_extracted", "summarize")
    graph.add_edge("summarize", "validate")
    graph.add_edge("validate", "persist")
    graph.add_edge("persist", "update_article")
    graph.add_edge("update_article", "embed")
    graph.add_edge("embed", "generate_quiz")
    graph.add_edge("generate_quiz", "persist_quiz")
    graph.add_edge("persist_quiz", END)

    return graph.compile()


def done_event_payload(state: RefreshState) -> dict:
    payload: dict = {"articleIds": persisted_article_ids(state)}
    if "reportDate" in state:
        payload["reportDate"] = state["reportDate"]
    return payload


def persisted_article_ids(state: RefreshState) -> list[str]:
    ids = state.get("persistedArticleIds") or [
        article["id"] for article in state.get("articles", [])
    ]

    unique_ids = []
    seen = set()
    for article_id in ids:
        if article_id not in seen:
            unique_ids.append(article_id)
            seen.add(article_id)

    return unique_ids
