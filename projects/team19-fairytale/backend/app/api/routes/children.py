from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import get_current_user
from app.models.api import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    ExperienceCreateRequest,
    ExperienceResponse,
)
from app.services.children import (
    create_child,
    create_experience,
    delete_child,
    get_child_by_id,
    get_children_by_user,
    get_experiences_by_child,
    update_child,
)

router = APIRouter(prefix="/children", tags=["children"])


async def _get_owned_child(
    child_id: str,
    current_user: Mapping[str, object],
) -> Mapping[str, object]:
    child = await get_child_by_id(child_id)
    if child is None or child["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found.",
        )
    return child


@router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
async def create_child_endpoint(
    payload: ChildCreateRequest,
    current_user: Mapping[str, object] = Depends(get_current_user),
) -> ChildResponse:
    child = await create_child(
        user_id=str(current_user["id"]),
        name=payload.name,
        age=payload.age,
        personality=payload.personality,
        favorite_character=payload.favorite_character,
        favorite_toy=payload.favorite_toy,
        family_relationship=payload.family_relationship,
    )
    return ChildResponse.model_validate(child)


@router.get("", response_model=list[ChildResponse])
async def list_children(
    current_user: Mapping[str, object] = Depends(get_current_user),
) -> list[ChildResponse]:
    children = await get_children_by_user(str(current_user["id"]))
    return [ChildResponse.model_validate(c) for c in children]


@router.get("/{child_id}", response_model=ChildResponse)
async def get_child(
    child_id: str,
    current_user: Mapping[str, object] = Depends(get_current_user),
) -> ChildResponse:
    child = await _get_owned_child(child_id, current_user)
    return ChildResponse.model_validate(child)


@router.put("/{child_id}", response_model=ChildResponse)
async def update_child_endpoint(
    child_id: str,
    payload: ChildUpdateRequest,
    current_user: Mapping[str, object] = Depends(get_current_user),
) -> ChildResponse:
    await _get_owned_child(child_id, current_user)

    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update.",
        )

    updated = await update_child(child_id, **fields)
    return ChildResponse.model_validate(updated)


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child_endpoint(
    child_id: str,
    current_user: Mapping[str, object] = Depends(get_current_user),
) -> None:
    await _get_owned_child(child_id, current_user)
    await delete_child(child_id)


@router.post(
    "/{child_id}/experiences",
    response_model=ExperienceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_experience_endpoint(
    child_id: str,
    payload: ExperienceCreateRequest,
    current_user: Mapping[str, object] = Depends(get_current_user),
) -> ExperienceResponse:
    await _get_owned_child(child_id, current_user)
    experience = await create_experience(
        child_id=child_id,
        content=payload.content,
        experienced_at=payload.experienced_at,
    )
    return ExperienceResponse.model_validate(experience)


@router.get(
    "/{child_id}/experiences",
    response_model=list[ExperienceResponse],
)
async def list_experiences(
    child_id: str,
    current_user: Mapping[str, object] = Depends(get_current_user),
) -> list[ExperienceResponse]:
    await _get_owned_child(child_id, current_user)
    experiences = await get_experiences_by_child(child_id)
    return [ExperienceResponse.model_validate(e) for e in experiences]
