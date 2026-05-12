from fastapi import APIRouter

from app.config import settings
from app.models.responses import TestnetConfigResponse
from app.services import config_service

router = APIRouter()


@router.get('/config', response_model=TestnetConfigResponse, status_code=200)
async def get_config() -> TestnetConfigResponse:
    return config_service.get_testnet_config(settings)
