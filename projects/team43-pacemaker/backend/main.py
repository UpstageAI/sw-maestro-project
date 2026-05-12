"""FastAPI 진입점. Flutter Web FE → /data/* (REST), /agent/chat (SSE)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import chat, data

app = FastAPI(title="43조 운동 스케줄링 에이전트", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*"],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(chat.router, prefix="/agent", tags=["agent"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
