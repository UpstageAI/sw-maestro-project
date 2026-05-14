import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any

from newspick_ai.env import require_refresh_environment
from newspick_ai.graph.config import CATEGORY_FEEDS
from newspick_ai.graph.cancellation import (
    DEFAULT_REFRESH_CANCELLATIONS,
    RefreshCancellationRegistry,
)
from newspick_ai.graph.refresh_graph import done_event_payload, persisted_article_ids
from newspick_ai.graph.state import RefreshState


SseEvent = tuple[str, dict]


def create_live_refresh_runner(
    *,
    resetter=None,
    collector,
    deduplicator,
    extractor,
    summarizer,
    validator,
    persistor,
    article_updater,
    embedder,
    quiz_generator,
    quiz_persistor,
    report_generator: Any | None = None,
    env_validator=require_refresh_environment,
    cancellations: RefreshCancellationRegistry = DEFAULT_REFRESH_CANCELLATIONS,
) -> Callable[[list[str], str | None, bool], AsyncIterator[SseEvent]]:
    async def refresh_runner(
        category_ids: list[str],
        run_id: str | None = None,
        reset: bool = False,
    ) -> AsyncIterator[SseEvent]:
        state: RefreshState = {"articles": [], "events": []}
        if category_ids:
            state["categoryIds"] = category_ids

        env_validator()

        if reset and resetter is not None:
            cancellations.check(run_id)
            await resetter.run()

        feeds = _selected_feeds(category_ids)
        total_feeds = len(feeds)
        cancellations.check(run_id)
        yield "step", {"step": "collect", "current": 0, "total": total_feeds}

        for index, (feed_url, category_label, source_name) in enumerate(
            feeds, start=1
        ):
            cancellations.check(run_id)
            state = _merge_state(
                state,
                collector.run(
                    state,
                    feed_url=feed_url,
                    category=category_label,
                    source_name=source_name,
                ),
            )
            cancellations.check(run_id)
            yield "step", {
                "step": "collect",
                "current": index,
                "total": total_feeds,
            }

        cancellations.check(run_id)
        state = _merge_state(state, deduplicator.run(state))
        cancellations.check(run_id)
        collected_total = len(state["articles"])
        yield "step", {"step": "extract", "current": 0, "total": collected_total}
        state = _merge_state(state, await extractor.run(state))
        cancellations.check(run_id)
        state = _filter_extracted(state)
        yield "step", {
            "step": "extract",
            "current": len(state["articles"]),
            "total": collected_total,
        }

        summarize_total = len(state["articles"])
        yield "step", {
            "step": "summarize",
            "current": 0,
            "total": summarize_total,
        }

        summarized_articles = []
        events = state["events"]
        for index, article in enumerate(state["articles"], start=1):
            cancellations.check(run_id)
            summarized_state = await asyncio.to_thread(
                summarizer.run,
                {**state, "articles": [article], "events": events},
            )
            summarized_articles.extend(summarized_state["articles"])
            events = summarized_state["events"]
            cancellations.check(run_id)
            yield "step", {
                "step": "summarize",
                "current": index,
                "total": summarize_total,
            }

        state = {**state, "articles": summarized_articles, "events": events}

        cancellations.check(run_id)
        state = _merge_state(state, validator.run(state))
        cancellations.check(run_id)
        yield "step", {"step": "save", "current": 0, "total": 1}
        state = _merge_state(state, await persistor.run(state))
        cancellations.check(run_id)
        state = _merge_state(state, await article_updater.run(state))
        cancellations.check(run_id)
        yield "step", {"step": "save", "current": 1, "total": 1}

        yield "step", {"step": "embed", "current": 0, "total": 1}
        state = _merge_state(state, await embedder.run(state))
        cancellations.check(run_id)
        yield "step", {"step": "embed", "current": 1, "total": 1}

        yield "step", {"step": "quiz", "current": 0, "total": 1}
        state = _merge_state(state, quiz_generator.run(state))
        cancellations.check(run_id)
        state = _merge_state(state, await quiz_persistor.run(state))
        cancellations.check(run_id)
        yield "step", {"step": "quiz", "current": 1, "total": 1}

        if report_generator is not None:
            yield "step", {"step": "report", "current": 0, "total": 1}
            result = await report_generator.generate(persisted_article_ids(state))
            state = {**state, "reportDate": result["date"]}
            yield "step", {"step": "report", "current": 1, "total": 1}

        cancellations.check(run_id)
        yield "done", done_event_payload(state)

    return refresh_runner


def _selected_feeds(category_ids: list[str]) -> list[tuple[str, str, str]]:
    selected_ids = category_ids or list(CATEGORY_FEEDS.keys())
    feeds: list[tuple[str, str, str]] = []
    for category_id in selected_ids:
        feed = CATEGORY_FEEDS[category_id]
        feeds.extend(
            (source["url"], feed["label"], source["source"])
            for source in feed["feeds"]
        )
    return feeds


def _filter_extracted(state: RefreshState) -> RefreshState:
    return {
        **state,
        "articles": [article for article in state["articles"] if "content" in article],
    }


def _merge_state(state: RefreshState, update: RefreshState) -> RefreshState:
    return {**state, **update}
