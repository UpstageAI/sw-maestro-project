from fastapi import APIRouter, HTTPException

from app.config import settings
from app.db.postgres import check_database_connection

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, object]:
    return {
        "status": "ok",
        "environment": settings.app_env,
        "supabase_url_configured": bool(settings.resolved_supabase_url),
        "database_url_configured": bool(settings.database_url),
    }


@router.get("/db")
async def database_health_check() -> dict[str, object]:
    if not settings.database_url:
        raise HTTPException(
            status_code=503,
            detail="Database settings are incomplete. Check backend/.env.",
        )

    try:
        db_info = await check_database_connection()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {exc}",
        ) from exc

    return {"status": "ok", "database": db_info}
