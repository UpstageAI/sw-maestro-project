from typing import Any, Optional

from pydantic import BaseModel

from app.models.dtos.job import JobDTO


class JobStatusResp(BaseModel):
    job_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

    @classmethod
    def from_dto(cls, dto: JobDTO) -> "JobStatusResp":
        return cls(
            job_id=dto.id,
            status=dto.status,
            result=dto.result,
            error=dto.error,
        )
