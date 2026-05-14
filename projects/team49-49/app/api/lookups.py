"""Shared 404 helpers for API routers.

Each helper looks up an entity, raises HTTPException(404) when it is missing,
and (when a workspace scope is provided) re-raises 404 when the entity exists
but belongs to a different workspace. This keeps cross-workspace access from
silently returning data and removes a class of duplicated try/except blocks
across the API surface.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.repositories.sqlite import SQLiteRepository


def workspace_or_404(repository: SQLiteRepository, workspace_id: int) -> dict[str, Any]:
    try:
        return repository.get_workspace(workspace_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def card_or_404(repository: SQLiteRepository, workspace_id: int, card_id: int) -> dict[str, Any]:
    try:
        card = repository.get_card(card_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if card["workspace_id"] != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card {card_id} not found in workspace {workspace_id}",
        )
    return card


def document_or_404(repository: SQLiteRepository, workspace_id: int, document_id: int) -> dict[str, Any]:
    try:
        document = repository.get_raw_document(document_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if document["workspace_id"] != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found in workspace {workspace_id}",
        )
    return document
