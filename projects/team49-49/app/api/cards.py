import re

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import get_repository
from app.api.lookups import card_or_404, workspace_or_404
from app.models.schemas import KnowledgeCardCreateRequest, KnowledgeCardDetail, KnowledgeCardRead, KnowledgeCardUpdate
from app.repositories.sqlite import SQLiteRepository
from app.services.paths import MultiHopPathService

router = APIRouter(prefix="/api/workspaces/{workspace_id}/cards", tags=["cards"])


@router.get(
    "",
    response_model=list[KnowledgeCardRead],
    summary="List cards",
    response_description="Knowledge cards in the workspace.",
)
def list_cards(
    workspace_id: int,
    card_type: str | None = None,
    status: str | None = None,
    confidence: str | None = None,
    keyword: str | None = None,
    tag: str | None = None,
    repository: SQLiteRepository = Depends(get_repository),
) -> list[dict]:
    return repository.list_cards(
        workspace_id=workspace_id,
        card_type=card_type,
        status=status,
        confidence=confidence,
        keyword=keyword,
        tag=tag,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=KnowledgeCardRead,
    summary="Create card",
    response_description="Created card. If no source ids are provided, a manual source document and chunk are created.",
    responses={400: {"description": "Invalid source ids."}, 404: {"description": "Workspace, document, or chunk not found."}},
)
def create_card(
    workspace_id: int,
    payload: KnowledgeCardCreateRequest,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    workspace_or_404(repository, workspace_id)
    source_document_id, source_chunk_id = _resolve_card_source(repository, workspace_id, payload)
    return repository.create_knowledge_card(
        workspace_id=workspace_id,
        source_document_id=source_document_id,
        source_chunk_id=source_chunk_id,
        card_type=payload.card_type,
        title=payload.title,
        summary=payload.summary,
        evidence_quote=payload.evidence_quote,
        keywords=payload.keywords,
        tags=payload.tags,
        status=payload.status,
        confidence=payload.confidence,
    )


@router.get(
    "/{card_id}",
    response_model=KnowledgeCardDetail,
    summary="Get card",
    responses={404: {"description": "Card not found in this workspace."}},
)
def get_card(workspace_id: int, card_id: int, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    card = card_or_404(repository, workspace_id, card_id)
    return {
        **card,
        "source_document": repository.get_raw_document(card["source_document_id"]),
        "source_chunk": repository.get_chunk(card["source_chunk_id"]),
        "relations": repository.list_relations(workspace_id, card_id=card_id),
    }


@router.patch(
    "/{card_id}",
    response_model=KnowledgeCardRead,
    summary="Update card",
    responses={404: {"description": "Card not found in this workspace."}},
)
def update_card(
    workspace_id: int,
    card_id: int,
    payload: KnowledgeCardUpdate,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    card_or_404(repository, workspace_id, card_id)
    return repository.update_card(
        card_id=card_id,
        card_type=payload.card_type,
        title=payload.title,
        summary=payload.summary,
        evidence_quote=payload.evidence_quote,
        keywords=payload.keywords,
        tags=payload.tags,
        status=payload.status,
        confidence=payload.confidence,
    )


@router.delete(
    "/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete card",
    responses={404: {"description": "Card not found in this workspace."}},
)
def delete_card(
    workspace_id: int,
    card_id: int,
    repository: SQLiteRepository = Depends(get_repository),
) -> Response:
    card_or_404(repository, workspace_id, card_id)
    repository.delete_card(card_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{card_id}/relations",
    summary="List card relations",
    responses={404: {"description": "Card not found in this workspace."}},
)
def list_card_relations(workspace_id: int, card_id: int, repository: SQLiteRepository = Depends(get_repository)) -> list[dict]:
    card_or_404(repository, workspace_id, card_id)
    return repository.list_relations(workspace_id, card_id=card_id)


@router.get(
    "/{card_id}/paths",
    summary="List multi-hop card paths",
    responses={404: {"description": "Card not found in this workspace."}},
)
def list_card_paths(
    workspace_id: int,
    card_id: int,
    depth: int = 2,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    try:
        return MultiHopPathService(repository).find_card_paths(
            workspace_id=workspace_id,
            card_id=card_id,
            depth=depth,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _resolve_card_source(
    repository: SQLiteRepository,
    workspace_id: int,
    payload: KnowledgeCardCreateRequest,
) -> tuple[int, int]:
    if payload.source_document_id is None and payload.source_chunk_id is None:
        document = repository.create_raw_document(
            workspace_id=workspace_id,
            filename=_manual_card_filename(payload.title),
            document_type="md",
            content=payload.evidence_quote,
            source_type="manual_card",
            source_url="",
            external_id="",
        )
        chunk = repository.create_chunks(
            document_id=document["id"],
            workspace_id=workspace_id,
            contents=[payload.evidence_quote],
        )[0]
        return document["id"], chunk["id"]

    if payload.source_document_id is None or payload.source_chunk_id is None:
        raise HTTPException(status_code=400, detail="source_document_id and source_chunk_id must be provided together.")

    try:
        document = repository.get_raw_document(payload.source_document_id)
        chunk = repository.get_chunk(payload.source_chunk_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if document["workspace_id"] != workspace_id or chunk["workspace_id"] != workspace_id:
        raise HTTPException(status_code=400, detail="Card source ids must belong to the target workspace.")
    if chunk["document_id"] != document["id"]:
        raise HTTPException(status_code=400, detail="source_chunk_id must belong to source_document_id.")
    return document["id"], chunk["id"]


def _manual_card_filename(title: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9가-힣_-]+", "-", title.strip()).strip("-").lower()
    return f"manual-card-{slug or 'card'}.md"
