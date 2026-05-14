import pytest

from newspick_ai.env import MissingEnvironmentError
from newspick_ai.graph.cancellation import RefreshCancellationRegistry, RefreshCancelled
from newspick_ai.graph.config import CATEGORY_FEEDS
from newspick_ai.graph.live_refresh import create_live_refresh_runner


class FakeCollector:
    def run(
        self,
        state,
        feed_url: str,
        category: str,
        source_name: str | None = None,
    ):
        article_id = feed_url.rsplit("/", 1)[-1]
        return {
            "articles": [
                *state["articles"],
                {
                    "id": article_id,
                    "url": feed_url,
                    "title": article_id,
                    "source": source_name or "Test",
                    "category": category,
                    "publishedAt": "2026-05-12T00:00:00Z",
                    "content": "body",
                    "status": "collected",
                },
            ],
            "events": state["events"],
        }


class RecordingCollector(FakeCollector):
    def __init__(self, log: list[str]):
        self._log = log

    def run(
        self,
        state,
        feed_url: str,
        category: str,
        source_name: str | None = None,
    ):
        self._log.append("collect")
        return super().run(state, feed_url, category, source_name)


class RecordingResetter:
    def __init__(self, log: list[str]):
        self._log = log

    async def run(self):
        self._log.append("reset")


class SyncIdentity:
    def run(self, state):
        return state


class AsyncIdentity:
    async def run(self, state):
        return state


class FakeSummarizer:
    def run(self, state):
        return {
            **state,
            "articles": [
                {
                    **article,
                    "summary": ["summary"],
                    "keywords": ["keyword"],
                    "importance": "important",
                    "context": "context",
                    "importanceScore": 5,
                }
                for article in state["articles"]
            ],
        }


class FakePersistor:
    async def run(self, state):
        return {
            **state,
            "persistedArticleIds": [article["id"] for article in state["articles"]],
        }


class FakeReportGenerator:
    async def generate(self, article_ids):
        return {"date": "2026-05-12"}


def _runner(
    cancellations: RefreshCancellationRegistry | None = None,
    report_generator=None,
    collector=None,
    resetter=None,
    env_validator=lambda: None,
):
    return create_live_refresh_runner(
        resetter=resetter,
        collector=collector or FakeCollector(),
        deduplicator=SyncIdentity(),
        extractor=AsyncIdentity(),
        summarizer=FakeSummarizer(),
        validator=SyncIdentity(),
        persistor=FakePersistor(),
        article_updater=AsyncIdentity(),
        embedder=AsyncIdentity(),
        quiz_generator=SyncIdentity(),
        quiz_persistor=AsyncIdentity(),
        report_generator=report_generator,
        env_validator=env_validator,
        cancellations=cancellations or RefreshCancellationRegistry(),
    )


@pytest.mark.asyncio
async def test_live_refresh_runner_emits_collect_step_per_feed():
    events = [event async for event in _runner()(["tech", "policy"], None)]
    total_feeds = len(CATEGORY_FEEDS["tech"]["feeds"]) + len(
        CATEGORY_FEEDS["policy"]["feeds"]
    )

    collect_events = [
        payload for name, payload in events if name == "step" and payload["step"] == "collect"
    ]

    assert collect_events == [
        {"step": "collect", "current": current, "total": total_feeds}
        for current in range(total_feeds + 1)
    ]


@pytest.mark.asyncio
async def test_live_refresh_runner_resets_before_collect_when_requested():
    log: list[str] = []

    events = [
        event
        async for event in _runner(
            collector=RecordingCollector(log),
            resetter=RecordingResetter(log),
        )(["tech"], None, True)
    ]

    assert log[:2] == ["reset", "collect"]
    assert events[-1] == ("done", {"articleIds": ["it", "03.xml", "health.xml"]})


@pytest.mark.asyncio
async def test_live_refresh_runner_validates_environment_before_reset_and_collect():
    log: list[str] = []

    def failing_env_validator():
        log.append("validate")
        raise MissingEnvironmentError("AI 설정을 읽지 못해 재수집을 완료하지 못했어요.")

    with pytest.raises(MissingEnvironmentError):
        async for _event in _runner(
            collector=RecordingCollector(log),
            resetter=RecordingResetter(log),
            env_validator=failing_env_validator,
        )(["tech"], None, True):
            pass

    assert log == ["validate"]


@pytest.mark.asyncio
async def test_live_refresh_runner_emits_summarize_step_per_article_and_done():
    events = [event async for event in _runner()(["tech"], None)]

    assert ("step", {"step": "extract", "current": 0, "total": 3}) in events
    assert ("step", {"step": "extract", "current": 3, "total": 3}) in events
    assert ("step", {"step": "summarize", "current": 0, "total": 3}) in events
    assert ("step", {"step": "summarize", "current": 3, "total": 3}) in events
    assert events[-1] == (
        "done",
        {"articleIds": ["it", "03.xml", "health.xml"]},
    )


@pytest.mark.asyncio
async def test_live_refresh_runner_emits_post_summary_steps_until_report_done():
    events = [
        event async for event in _runner(report_generator=FakeReportGenerator())(["tech"], None)
    ]

    assert ("step", {"step": "save", "current": 0, "total": 1}) in events
    assert ("step", {"step": "save", "current": 1, "total": 1}) in events
    assert ("step", {"step": "embed", "current": 0, "total": 1}) in events
    assert ("step", {"step": "embed", "current": 1, "total": 1}) in events
    assert ("step", {"step": "quiz", "current": 0, "total": 1}) in events
    assert ("step", {"step": "quiz", "current": 1, "total": 1}) in events
    assert ("step", {"step": "report", "current": 0, "total": 1}) in events
    assert ("step", {"step": "report", "current": 1, "total": 1}) in events


@pytest.mark.asyncio
async def test_live_refresh_runner_includes_report_date_after_full_pipeline():
    events = [
        event async for event in _runner(report_generator=FakeReportGenerator())(["tech"], None)
    ]

    assert events[-1] == (
        "done",
        {"articleIds": ["it", "03.xml", "health.xml"], "reportDate": "2026-05-12"},
    )


@pytest.mark.asyncio
async def test_live_refresh_runner_stops_after_cancel_before_next_stage():
    cancellations = RefreshCancellationRegistry()
    events = []

    with pytest.raises(RefreshCancelled):
        async for event in _runner(cancellations)(["tech"], "run-123"):
            events.append(event)
            if event == ("step", {"step": "collect", "current": 1, "total": 3}):
                cancellations.cancel("run-123")

    assert not [
        payload for name, payload in events if name == "step" and payload["step"] == "summarize"
    ]
