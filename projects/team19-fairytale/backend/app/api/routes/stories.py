from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies.auth import get_current_user
from app.db.postgres import get_db_connection
from app.exceptions import LLMUnavailableError, StoryGenerationError, StoryParsingError
from app.models.api import MessageResponse, StoryGenerateRequest, StoryGenerateResponse
from app.services.children import get_child_for_user
from app.services.story import generate_story as generate_story_service

router = APIRouter(prefix="/stories", tags=["stories"])


@router.post(
    "/generate",
    response_model=StoryGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_story(
    request: StoryGenerateRequest,
    user: Mapping[str, object] = Depends(get_current_user),
) -> StoryGenerateResponse:
    user_id = str(user["id"])

    child = await get_child_for_user(request.child_id, user_id)
    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found or does not belong to the current user.",
        )

    async with get_db_connection() as db:
        try:
            row = await generate_story_service(child, request, db)
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except StoryParsingError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
        except StoryGenerationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    return StoryGenerateResponse(**row)


@router.get(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def list_story_history() -> MessageResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Story history endpoint is planned for Phase 5.",
    )


@router.post(
    "/{story_id}/regenerate",
    response_model=MessageResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def regenerate_story(story_id: str = Path(...)) -> MessageResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Regenerate endpoint for story '{story_id}' is planned for Phase 6.",
    )
