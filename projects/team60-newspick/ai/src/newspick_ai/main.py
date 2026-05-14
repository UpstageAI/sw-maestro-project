import asyncio
import logging
import os
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from newspick_ai.env import load_environment
from newspick_ai.api.chat_stream import create_chat_stream_router
from newspick_ai.api.refresh_stream import create_refresh_stream_router
from newspick_ai.api.report import create_report_router
from newspick_ai.graph.article_updater import ArticleUpdater
from newspick_ai.graph.collector import RssCollector
from newspick_ai.graph.content_extractor import ContentExtractor
from newspick_ai.graph.deduplicator import Deduplicator
from newspick_ai.graph.embedder import Embedder
from newspick_ai.graph.live_refresh import create_live_refresh_runner
from newspick_ai.graph.persistor import Persistor
from newspick_ai.graph.quiz_generator import QuizGenerator
from newspick_ai.graph.quiz_persistor import QuizPersistor
from newspick_ai.graph.refresh_resetter import RefreshResetter
from newspick_ai.graph.summarizer import Summarizer
from newspick_ai.graph.summary_validator import SummaryValidator
from newspick_ai.report.generator import DailyReportGenerator

load_environment()

_collector = RssCollector()
_resetter = RefreshResetter()
_deduplicator = Deduplicator()
_extractor = ContentExtractor()
_summarizer = Summarizer()
_validator = SummaryValidator()
_persistor = Persistor()
_article_updater = ArticleUpdater()
_embedder = Embedder()
_quiz_generator = QuizGenerator()
_quiz_persistor = QuizPersistor()

_report_generator = DailyReportGenerator()
_refresh_runner = create_live_refresh_runner(
    resetter=_resetter,
    collector=_collector,
    deduplicator=_deduplicator,
    extractor=_extractor,
    summarizer=_summarizer,
    validator=_validator,
    persistor=_persistor,
    article_updater=_article_updater,
    embedder=_embedder,
    quiz_generator=_quiz_generator,
    quiz_persistor=_quiz_persistor,
    report_generator=_report_generator,
)


logger = logging.getLogger(__name__)


async def _run_batch():
    logger.info("배치 파이프라인 시작")
    async for event_name, payload in _refresh_runner([], None):
        if event_name == "step":
            logger.info(
                "[%s] %d/%d",
                payload.get("step"),
                payload.get("current", 0),
                payload.get("total", 0),
            )
        elif event_name == "done":
            logger.info("배치 완료 — 총 %d건 처리", len(payload.get("articleIds", [])))
        elif event_name == "error":
            logger.error("배치 오류 [%s]: %s", event_name, payload.get("message"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_run_batch, CronTrigger(hour=6, minute=0, timezone="Asia/Seoul"))
    scheduler.start()
    if os.getenv("NEWSPICK_RUN_STARTUP_BATCH", "").lower() == "true":
        asyncio.create_task(_run_batch())
    yield
    scheduler.shutdown()


app = FastAPI(title="NewPick AI", version="0.0.1", lifespan=lifespan)

app.include_router(
    create_refresh_stream_router(refresh_runner=_refresh_runner)
)
app.include_router(create_chat_stream_router())
app.include_router(create_report_router(_report_generator))


@app.get("/health")
async def health():
    return {"status": "ok"}
