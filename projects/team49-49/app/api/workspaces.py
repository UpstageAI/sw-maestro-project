from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_repository
from app.api.lookups import workspace_or_404
from app.models.schemas import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.repositories.sqlite import SQLiteRepository

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=WorkspaceRead,
    summary="Create workspace",
    response_description="Created workspace.",
)
def create_workspace(payload: WorkspaceCreate, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    return repository.create_workspace(payload.name, payload.description)


@router.get(
    "",
    response_model=list[WorkspaceRead],
    summary="List workspaces",
    response_description="Workspaces ordered by id.",
)
def list_workspaces(repository: SQLiteRepository = Depends(get_repository)) -> list[dict]:
    return repository.list_workspaces()


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    summary="Get workspace",
    responses={404: {"description": "Workspace not found."}},
)
def get_workspace(workspace_id: int, repository: SQLiteRepository = Depends(get_repository)) -> dict:
    return workspace_or_404(repository, workspace_id)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    summary="Update workspace",
    responses={404: {"description": "Workspace not found."}},
)
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    workspace_or_404(repository, workspace_id)
    return repository.update_workspace(
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
    )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workspace",
    responses={404: {"description": "Workspace not found."}},
)
def delete_workspace(workspace_id: int, repository: SQLiteRepository = Depends(get_repository)) -> Response:
    workspace_or_404(repository, workspace_id)
    repository.delete_workspace(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
