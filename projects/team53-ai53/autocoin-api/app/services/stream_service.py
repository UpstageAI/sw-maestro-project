import asyncio
import json
import logging
from typing import Any

import websockets

from app.models.responses import StreamStatusResponse

logger = logging.getLogger(__name__)

_STREAM_NAME = "btcusdt@ticker"
_connected: bool = False
_last_event: dict[str, Any] | None = None
_task: asyncio.Task | None = None


def get_stream_status() -> StreamStatusResponse:
    return StreamStatusResponse(
        connected=_connected,
        stream_name=_STREAM_NAME if _connected else None,
        last_event=_last_event,
    )


async def _listen(ws_stream_url: str) -> None:
    global _connected, _last_event
    url = f"{ws_stream_url}/{_STREAM_NAME}"
    while True:
        try:
            async with websockets.connect(url) as ws:
                _connected = True
                logger.info("WebSocket connected: %s", url)
                async for raw in ws:
                    event = json.loads(raw)
                    _last_event = event
            _connected = False
        except Exception:
            logger.exception("WebSocket disconnected, retrying in 5s")
            _connected = False
            await asyncio.sleep(5)


def start_stream(ws_stream_url: str) -> None:
    global _task
    if _task and not _task.done():
        logger.warning("Stream background task is already running.")
        return
    _task = asyncio.create_task(_listen(ws_stream_url))
    logger.info("Stream background task started")


async def stop_stream() -> None:
    global _task, _connected
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _connected = False
    logger.info("Stream background task stopped")
