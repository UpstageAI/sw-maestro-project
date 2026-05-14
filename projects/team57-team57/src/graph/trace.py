"""Tiny helper for node timing + log entry assembly.

Usage:
    with measure("classifier", "llm") as log:
        # ... do work ...
        log["summary"] = "sentiment=negative ..."
        log["details"] = {"model": "...", "prompt_preview": "..."}
    return {..., "node_log": [log]}
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator


@contextmanager
def measure(node: str, kind: str) -> Iterator[dict[str, Any]]:
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    log: dict[str, Any] = {
        "node": node,
        "started_at": started,
        "kind": kind,
        "summary": "",
        "details": {},
    }
    try:
        yield log
    finally:
        log["duration_ms"] = int((time.perf_counter() - t0) * 1000)
