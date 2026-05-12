from fastapi import FastAPI

from app.api.router import api_router
from app.config import settings


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
    )

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "environment": settings.app_env,
            "docs": "/docs",
        }

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_application()
