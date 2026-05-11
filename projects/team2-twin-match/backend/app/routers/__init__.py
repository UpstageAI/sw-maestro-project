from fastapi import APIRouter

from app.routers import agents, conversations, health, jobs

router = APIRouter()

# Health & root live at the top level (no /api prefix), per spec §4.1.
router.include_router(health.router, tags=["system"])

# All business endpoints are mounted under /api, per spec §4.2-4.4.
api_router = APIRouter(prefix="/api")
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["conversations"]
)
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

router.include_router(api_router)
