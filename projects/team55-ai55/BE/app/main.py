import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.services.metrics import record_agent_failure


TASK_INFO_REQUIRED_FIELDS = {"title", "importance", "status"}
DEFAULT_FRONTEND_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def frontend_origins() -> list[str]:
    raw = os.getenv("FRONTEND_ORIGINS")
    if not raw:
        return list(DEFAULT_FRONTEND_ORIGINS)
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


def task_info_missing_details(errors: list[dict]) -> dict | None:
    fields: set[str] = set()
    task_indices: set[int] = set()
    for error in errors:
        loc = error.get("loc", ())
        if (
            error.get("type") == "missing"
            and len(loc) >= 5
            and loc[:3] == ("body", "snapshot", "tasks")
            and isinstance(loc[3], int)
            and loc[4] in TASK_INFO_REQUIRED_FIELDS
        ):
            task_indices.add(loc[3])
            fields.add(loc[4])
    if not fields:
        return None
    return {"task_indices": sorted(task_indices), "fields": sorted(fields)}


def create_app() -> FastAPI:
    app = FastAPI(title="AI SWM Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    request_times: dict[str, deque[float]] = defaultdict(deque)
    rate_limit = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))

    @app.middleware("http")
    async def rate_limit_middleware(request, call_next):
        if rate_limit <= 0 or request.method == "OPTIONS":
            return await call_next(request)
        now = time.monotonic()
        key = request.client.host if request.client else "unknown"
        bucket = request_times[key]
        while bucket and now - bucket[0] >= 60:
            bucket.popleft()
        if len(bucket) >= rate_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "잠시 후 다시 시도해 주세요.",
                        "details": {"limit_per_minute": rate_limit},
                    }
                },
            )
        bucket.append(now)
        return await call_next(request)

    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_, exc: RequestValidationError):
        task_info_details = task_info_missing_details(exc.errors())
        if task_info_details:
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "task_info_insufficient",
                        "message": "Task 필수 정보를 입력해 주세요.",
                        "details": task_info_details,
                    }
                },
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "입력값 형식이 올바르지 않습니다.",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(Exception)
    async def internal_exception_handler(_, __: Exception):
        record_agent_failure("unknown", "internal_error")
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": "agent_failed",
                    "message": "AI 분석 일부가 실패했습니다. 다시 시도해 주세요.",
                    "details": {},
                }
            },
        )

    return app


app = create_app()
