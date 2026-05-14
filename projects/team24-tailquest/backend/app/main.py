import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.materials import router as materials_router
from app.api.sessions import router as sessions_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Demo-friendly stage logs (LangGraph nodes, Solar timing, auth events).
    from app.log_format import setup_logging, stage
    setup_logging()
    stage("🚀 [BOOT] tail-question backend 시작")

    # Warm-build the LangGraph compiled graph at startup so first-request latency
    # doesn't include compilation overhead.
    from app.graph.workflow import get_graph
    get_graph()
    stage("✓ [BOOT] LangGraph 컴파일 완료")

    # Ensure materials upload directory exists. Chroma persist directory is
    # initialized eagerly in app.storage.chroma at import time.
    cfg = get_settings()
    Path(cfg.materials_upload_dir).mkdir(parents=True, exist_ok=True)
    # Touch the chroma module so the persistent client gets initialized at
    # boot rather than on first request.
    from app.storage import chroma  # noqa: F401

    # Bootstrap the SQLite session/turn store.
    Path(cfg.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    from app.storage.db import init_db
    init_db()

    # Recover orphan "indexing" materials. A previous uvicorn process may
    # have crashed mid-ingest leaving rows in indexing status with no
    # background worker still running them — flip those to failed so the
    # FE stops polling forever.
    from app.services import material_store
    n = material_store.mark_indexing_as_failed(
        "서버 재시작 중 인덱싱이 중단되었습니다. 다시 추가해주세요.",
    )
    if n:
        import logging
        logging.getLogger(__name__).info(
            "boot: marked %d orphan indexing materials as failed", n
        )

    yield


app = FastAPI(
    title="꼬리질문 Backend",
    version="0.1.0",
    description="기술 면접 꼬리질문 생성기 백엔드 (24조)",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Random per-process token. Frontend stores this and re-checks on page load;
# a mismatch means the backend has restarted, so the cached login is cleared
# and the user is sent back to /login.
BOOT_ID = secrets.token_urlsafe(8)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "model": settings.solar_model,
        "mock": settings.use_mock_llm,
        "key_configured": bool(settings.upstage_api_key),
        "boot_id": BOOT_ID,
    }


app.include_router(sessions_router)
app.include_router(materials_router)
app.include_router(auth_router)
