"""FR-006: 비동기 작업 상태 폴링."""

from app.core.errors.error import JobNotFoundException
from app.models.dtos.job import JobDTO
from app.repositories.job_repository import JobRepository


class JobService:
    def __init__(self, job_repository: JobRepository):
        self.job_repository = job_repository

    async def get_status(self, job_id: str) -> JobDTO:
        job = await self.job_repository.get_by_id(job_id)
        if job is None:
            raise JobNotFoundException()
        return job
