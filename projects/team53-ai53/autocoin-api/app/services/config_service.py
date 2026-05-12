from app.config import Settings
from app.models.responses import TestnetConfigResponse


def get_testnet_config(settings: Settings) -> TestnetConfigResponse:
    return TestnetConfigResponse(
        rest_base_url=settings.binance_testnet_rest_base_url,
        ws_stream_url=settings.binance_testnet_ws_stream_url,
        ws_api_url=settings.binance_testnet_ws_api_url,
    )
