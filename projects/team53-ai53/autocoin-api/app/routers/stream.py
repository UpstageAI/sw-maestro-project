from fastapi import APIRouter

from app.models.responses import StreamStatusResponse
from app.services import stream_service

router = APIRouter()


@router.get("/stream/status", response_model=StreamStatusResponse, status_code=200)
async def get_stream_status() -> StreamStatusResponse:
    return stream_service.get_stream_status()
