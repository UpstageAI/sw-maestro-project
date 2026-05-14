import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from newspick_ai.env import MissingEnvironmentError
from newspick_ai.graph.config import parse_category_ids
from newspick_ai.graph.cancellation import (
    DEFAULT_REFRESH_CANCELLATIONS,
    RefreshCancellationRegistry,
    RefreshCancelled,
)
from newspick_ai.graph.refresh_graph import done_event_payload, persisted_article_ids


SseEvent = tuple[str, dict]
RefreshRunner = Callable[[list[str], str | None, bool], AsyncIterator[SseEvent]]


async def default_refresh_runner(
    category_ids: list[str],
    run_id: str | None = None,
    reset: bool = False,
) -> AsyncIterator[SseEvent]:
    yield "done", {"articleIds": []}


def create_graph_refresh_runner(graph: Any, report_generator: Any | None = None) -> RefreshRunner:
    async def refresh_runner(
        category_ids: list[str],
        run_id: str | None = None,
        reset: bool = False,
    ) -> AsyncIterator[SseEvent]:
        initial_state = {"articles": [], "events": []}
        if category_ids:
            initial_state["categoryIds"] = category_ids

        state = await graph.ainvoke(initial_state)
        for event in state.get("events", []):
            yield "step", event

        if report_generator is not None:
            result = await report_generator.generate(persisted_article_ids(state))
            state = {**state, "reportDate": result["date"]}

        yield "done", done_event_payload(state)

    return refresh_runner


def create_refresh_stream_router(
    refresh_runner: RefreshRunner = default_refresh_runner,
    cancellations: RefreshCancellationRegistry = DEFAULT_REFRESH_CANCELLATIONS,
) -> APIRouter:
    router = APIRouter()

    @router.get("/refresh-stream")
    async def refresh_stream(
        categories: str | None = Query(default=None),
        run_id: str | None = Query(default=None, alias="runId"),
        reset: bool = Query(default=False),
    ):
        try:
            category_ids = parse_category_ids(categories)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return StreamingResponse(
            _event_stream(refresh_runner, cancellations, category_ids, run_id, reset),
            media_type="text/event-stream",
        )

    @router.post("/refresh-stream/{run_id}/cancel", status_code=204)
    async def cancel_refresh_stream(run_id: str):
        cancellations.cancel(run_id)
        return Response(status_code=204)

    return router


async def _event_stream(
    refresh_runner: RefreshRunner,
    cancellations: RefreshCancellationRegistry,
    category_ids: list[str],
    run_id: str | None,
    reset: bool,
) -> AsyncIterator[str]:
    cancellations.register(run_id)
    try:
        async for event_name, payload in refresh_runner(category_ids, run_id, reset):
            yield format_sse(event_name, payload)
    except RefreshCancelled:
        yield format_sse(
            "error",
            {"code": "refresh_cancelled", "message": "refresh cancelled"},
        )
    except MissingEnvironmentError as exc:
        yield format_sse(
            "error",
            {"code": "missing_environment", "message": str(exc)},
        )
    except Exception as exc:
        yield format_sse(
            "error",
            {"code": "refresh_failed", "message": str(exc)},
        )
    finally:
        cancellations.complete(run_id)


def format_sse(event_name: str, payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_name}\ndata: {data}\n\n"
