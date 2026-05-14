from fastapi import FastAPI

from app.modules.combination_generator.router import router as combination_generator_router
from app.modules.mentor.router import router as mentor_router
from app.modules.mentor_candidate.router import router as mentor_candidate_router
from app.modules.report.router import router as report_router
from app.modules.team_profile.router import router as team_profile_router

app = FastAPI(title="Mentor-Fit API", version="0.1.0")

app.include_router(mentor_candidate_router)
app.include_router(team_profile_router)
app.include_router(combination_generator_router)
app.include_router(mentor_router)
app.include_router(report_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
