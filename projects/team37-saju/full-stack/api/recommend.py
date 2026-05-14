"""Vercel Python function — POST /api/recommend.

Runs the full 6-agent LangGraph pipeline and returns a single JSON payload
with the final result and the in-order event log.
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

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from _lib.parse import ParseError, parse_pipeline_request
from _lib.pipeline import run_pipeline_buffered

app = FastAPI()


def _json_response(body: object, status: int) -> JSONResponse:
    return JSONResponse(
        content=body,
        status_code=status,
        headers={"cache-control": "no-store"},
    )


@app.post("/api/recommend")
async def recommend(request: Request) -> JSONResponse:
    parsed = await parse_pipeline_request(request)
    if isinstance(parsed, ParseError):
        return _json_response({"error": parsed.error}, parsed.status)

    result, events = await run_pipeline_buffered(
        parsed.api_key, parsed.user_input, parsed.model
    )

    if result is None:
        error_event = next(
            (e for e in events if e.get("type") == "error"),
            None,
        )
        message = (
            (error_event or {}).get("message")
            or "파이프라인 실행에 실패했어요."
        )
        return _json_response({"error": message, "events": events}, 400)

    return _json_response({"result": result, "events": events}, 200)
