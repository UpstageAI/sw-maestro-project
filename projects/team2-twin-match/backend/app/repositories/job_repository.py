"""Job CRUD against `jobs` table."""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dtos.job import JobDTO


class JobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, conversation_id: str) -> JobDTO:
        """Insert a new Job in `pending` state."""
        raise NotImplementedError

    async def get_by_id(self, job_id: str) -> Optional[JobDTO]:
        """JSON-decode `result` before returning the DTO."""
        raise NotImplementedError

    async def update_status(
        self,
        job_id: str,
        *,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> Optional[JobDTO]:
        """Update status; JSON-encode `result` when provided."""
        raise NotImplementedError
