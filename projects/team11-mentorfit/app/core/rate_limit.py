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


async def _limit_endpoint(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
    detail: str,
) -> None:
    now = time.monotonic()
    window_start = now - window_seconds
    key = f"{bucket}:{_client_key(request)}"
    timestamps = _requests[key]

    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()

    if len(timestamps) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )

    timestamps.append(now)


async def limit_llm_endpoint(request: Request) -> None:
    await _limit_endpoint(
        request,
        bucket="llm",
        limit=settings.llm_endpoint_rate_limit,
        window_seconds=settings.llm_endpoint_rate_window_seconds,
        detail="LLM 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )


async def limit_recommendation_endpoint(request: Request) -> None:
    await _limit_endpoint(
        request,
        bucket="recommendation",
        limit=settings.recommendation_endpoint_rate_limit,
        window_seconds=settings.recommendation_endpoint_rate_window_seconds,
        detail="추천 생성 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )
