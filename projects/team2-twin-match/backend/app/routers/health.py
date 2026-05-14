from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app.core.config import config
from app.core.db.session import ping_db
from app.models.schemas.common import HealthResponse

router = APIRouter()


@router.get("/")
async def root() -> dict:
    return {
        "message": config.TITLE,
        "status": "running",
        "version": config.VERSION,
        "docs": config.DOCS_URL or None,
        "health": "/health",
    }


@router.get("/health", response_model=HealthResponse)
async def health() -> ORJSONResponse:
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        await ping_db()
        body = {"status": "healthy", "database": "connected", "timestamp": timestamp}
        return ORJSONResponse(status_code=200, content=body)
    except Exception:
        body = {
            "status": "unhealthy",
            "database": "disconnected",
            "timestamp": timestamp,
        }
        return ORJSONResponse(status_code=500, content=body)
