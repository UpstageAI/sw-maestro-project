from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.cards import router as cards_router
from app.api.documents import router as documents_router
from app.api.graph import router as graph_router
from app.api.health import router as health_router
from app.api.qa import router as qa_router
from app.api.reviews import router as reviews_router
from app.api.search import router as search_router
from app.api.workflows import router as workflows_router
from app.api.workspaces import router as workspaces_router
from app.core.config import get_settings
from app.db.connection import resolve_sqlite_path
from app.repositories.sqlite import SQLiteRepository
from app.services.langgraph_remote import build_remote_langgraph_client
from app.services.llm import build_llm_client
from app.services.source_connectors import build_source_connector_registry
from app.web.routes import router as web_router


def create_app(repository: SQLiteRepository | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Ideation Context Hub API for managing workspaces, source documents, "
            "knowledge cards, graph relations, search, QA, and quality review workflows."
        ),
        version="0.1.0",
        openapi_tags=[
            {"name": "workspaces", "description": "Create, read, update, and delete workspace containers."},
            {"name": "documents", "description": "Ingest source links, pasted text, and uploaded files."},
            {"name": "cards", "description": "Create, read, update, delete, filter, and inspect Knowledge Cards."},
            {"name": "graph", "description": "Build document-card-relation graph views."},
            {"name": "search", "description": "Search cards/chunks and generate grounded answers."},
            {"name": "qa", "description": "Ask workspace questions and read QA history."},
            {"name": "reviews", "description": "Run quality review workflows for cards and relations."},
            {"name": "workflows", "description": "Inspect local workflow registry metadata."},
        ],
    )
    app.state.settings = settings
    app.state.repository = repository or SQLiteRepository(resolve_sqlite_path(settings.database_url))
    app.state.repository.initialize()
    app.state.llm_client = build_llm_client(settings)
    app.state.remote_langgraph_client = build_remote_langgraph_client(settings)
    app.state.source_connector_registry = build_source_connector_registry(settings)
    frontend_assets = Path(__file__).resolve().parents[1] / "frontend" / "dist" / "assets"
    if frontend_assets.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_assets)), name="frontend-assets")
    app.include_router(web_router)
    app.include_router(health_router)
    app.include_router(workspaces_router)
    app.include_router(documents_router)
    app.include_router(cards_router)
    app.include_router(search_router)
    app.include_router(qa_router)
    app.include_router(reviews_router)
    app.include_router(graph_router)
    app.include_router(workflows_router)
    return app


app = create_app()
