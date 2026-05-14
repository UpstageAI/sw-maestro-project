from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

_requests: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


async def limit_llm_endpoint(request: Request) -> None:
    now = time.monotonic()
    window_start = now - settings.llm_endpoint_rate_window_seconds
    key = _client_key(request)
    timestamps = _requests[key]

    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()

    if len(timestamps) >= settings.llm_endpoint_rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="LLM 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
        )

    timestamps.append(now)
