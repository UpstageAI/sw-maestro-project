from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routes.auth import router as auth_router
from app.routes.availability import router as availability_router
from app.routes.schedules import router as schedules_router

load_dotenv()

app = FastAPI(title="Kairos Schedule Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(schedules_router, prefix="/api/schedules", tags=["schedules"])
app.include_router(availability_router, prefix="/api/availability", tags=["availability"])
