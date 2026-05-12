"""FastAPI WAS — uvicorn으로 8000번에 띄워서 프론트(static) + API 모두 서빙."""
import logging
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import config
from src.api.routes import session

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

app = FastAPI(title="GitHub Portfolio Agent")
app.include_router(session.router)

STATIC_DIR = config.ROOT / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/app")
def app_page() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "app.html"))


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "model": config.MODEL_NAME,
        "effort_fast": config.EFFORT_FAST,
        "effort_deep": config.EFFORT_DEEP,
        "score_threshold": config.SCORE_THRESHOLD,
        "max_refine_iter": config.MAX_REFINE_ITER,
    }
