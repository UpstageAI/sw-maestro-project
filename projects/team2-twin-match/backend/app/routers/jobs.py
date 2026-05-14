"""FR-006 endpoint."""

from fastapi import APIRouter, Depends

from app.models.schemas.common import ErrorResponse
from app.models.schemas.job import JobStatusResp
from app.routers.dependencies import get_job_service
from app.services.job_service import JobService

router = APIRouter()


@router.get(
    "/{job_id}",
    response_model=JobStatusResp,
    responses={404: {"model": ErrorResponse}},
)
async def get_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
) -> JobStatusResp:
    """GET /api/jobs/{job_id} — 작업 상태 조회 (폴링)."""
    dto = await service.get_status(job_id)
    return JobStatusResp.from_dto(dto)
