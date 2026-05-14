from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api.dependencies import get_repository
from app.repositories.sqlite import SQLiteRepository
from app.services.retrieval import RetrievalService
from app.workflows.qa import RetrievalQAWorkflow

router = APIRouter(prefix="/api/workspaces/{workspace_id}/search", tags=["search"])


class LLMSearchRequest(BaseModel):
    query: str = Field(min_length=1)


@router.get("")
def search_workspace(
    workspace_id: int,
    q: str = Query(min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    card_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    confidence: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    filters = {
        "card_type": card_type,
        "status": status,
        "confidence": confidence,
        "source_type": source_type,
    }
    return RetrievalService(repository).search(
        workspace_id=workspace_id,
        query=q,
        top_k=top_k,
        filters=filters,
    )


@router.post("/llm")
def llm_search_workspace(
    request: Request,
    workspace_id: int,
    payload: LLMSearchRequest,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    settings = request.app.state.settings
    answer = RetrievalQAWorkflow(
        repository,
        upstage_api_key=settings.upstage_api_key,
    ).answer(
        workspace_id=workspace_id,
        question=payload.query,
    )
    return {"query": payload.query, **answer}
