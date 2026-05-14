from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from app.generator import generate_patent_document
except ImportError:
    from backend.app.generator import generate_patent_document


class GenerateRequest(BaseModel):
    idea: str = Field(..., min_length=1, max_length=300)
    tone: str = "serious"
    use_search: bool = True


app = FastAPI(
    title="Brainrot Patent API",
    description="2-week MVP mock backend for AI-generated patent-style documents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/generate")
def generate(request: GenerateRequest) -> dict:
    return generate_patent_document(
        idea=request.idea.strip(),
        tone=request.tone,
        use_search=request.use_search,
    )
