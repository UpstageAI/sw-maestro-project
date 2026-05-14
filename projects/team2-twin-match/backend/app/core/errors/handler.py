from fastapi import Request
from fastapi.responses import ORJSONResponse

from app.core.errors.error import BaseAPIException


async def api_error_handler(_: Request, exc: BaseAPIException) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
