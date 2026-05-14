"""Vercel Python function — POST /api/recommend/stream.

Server-Sent Events: emits per-agent progress as the LangGraph pipeline runs
and a terminal ``pipeline_done`` (or ``error``) event before closing the
stream.
"""

from __future__ import annotations

# Put the `api/` directory on sys.path so `_lib.*` imports resolve regardless
# of where Vercel's Python runtime mounts the function. This must run BEFORE
# any `from _lib...` imports.
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_search = _HERE
while True:
    if os.path.isdir(os.path.join(_search, "_lib")):
        if _search not in sys.path:
            sys.path.insert(0, _search)
        break
    _parent = os.path.dirname(_search)
    if _parent == _search:
        break
    _search = _parent

import asyncio
import json
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from _lib.parse import ParseError, parse_pipeline_request
from _lib.pipeline import stream_pipeline_events
from _lib.state import make_event

app = FastAPI()

HEARTBEAT_SECONDS = 15.0


def _format_sse(event: dict) -> bytes:
    event_type = event.get("type") or "message"
    return (
        f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
    ).encode("utf-8")


async def _merged_stream(
    events: AsyncIterator[dict],
    request: Request,
) -> AsyncIterator[bytes]:
    """Yield SSE bytes from the pipeline event iterator with heartbeats and
    early termination when the client disconnects.
    """
    iterator = events.__aiter__()
    next_task: asyncio.Task | None = None
    try:
        while True:
            if await request.is_disconnected():
                return

            if next_task is None:
                next_task = asyncio.ensure_future(iterator.__anext__())

            done, _pending = await asyncio.wait(
                {next_task}, timeout=HEARTBEAT_SECONDS
            )

            if not done:
                # Heartbeat: no event in HEARTBEAT_SECONDS — send a comment line.
                yield b": ping\n\n"
                continue

            try:
                event = next_task.result()
            except StopAsyncIteration:
                return
            except Exception as err:  # noqa: BLE001 — surface as SSE error
                yield _format_sse(
                    make_event("error", message=str(err) or "알 수 없는 오류가 발생했어요.")
                )
                return
            finally:
                next_task = None

            yield _format_sse(event)
    finally:
        if next_task is not None and not next_task.done():
            next_task.cancel()
            try:
                await next_task
            except BaseException:  # noqa: BLE001 — cleanup only
                pass


@app.post("/api/recommend/stream")
async def recommend_stream(request: Request):
    parsed = await parse_pipeline_request(request)
    if isinstance(parsed, ParseError):
        return JSONResponse(
            content={"error": parsed.error},
            status_code=parsed.status,
        )

    event_iter = stream_pipeline_events(
        parsed.api_key, parsed.user_input, parsed.model
    )

    return StreamingResponse(
        _merged_stream(event_iter, request),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "cache-control": "no-cache, no-transform",
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )
