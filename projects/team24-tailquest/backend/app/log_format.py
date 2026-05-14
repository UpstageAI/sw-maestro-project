"""Demo-friendly logging helper.

Goal: surface the LangGraph workflow, Solar API calls, and auth events as a
readable flow on screen during a recorded walkthrough. Keep the format short
enough to scan in real-time and consistent enough that viewers can match a
log line back to the corresponding code.

Output style:
  ▶ [ANALYZER]   start | question='Spring Framework와…' answer_len=8
  📡 [SOLAR]      structured_chat AnalysisOutput temp=0.2
  ⏱  [SOLAR]      done | elapsed=2.41s
  ✓ [ANALYZER]   done | quality=uncertain notes=1

Use `stage()` for one-shot markers and `timed()` (async-aware) for blocks
whose latency you want to surface.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager, contextmanager

# Single logger so every demo line shares a prefix and a viewer can scroll
# back to find a node by name.
log = logging.getLogger("tq.demo")


def _fmt_kv(kwargs: dict) -> str:
    parts: list[str] = []
    for k, v in kwargs.items():
        if isinstance(v, str):
            v_disp = v if len(v) <= 60 else v[:57] + "…"
            parts.append(f"{k}={v_disp!r}")
        else:
            parts.append(f"{k}={v}")
    return " | " + " ".join(parts) if parts else ""


def stage(label: str, **kwargs) -> None:
    """One-line stage marker. `label` should be like '▶ [ANALYZER] start'."""
    log.info(label + _fmt_kv(kwargs))


@contextmanager
def timed(label: str, **kwargs):
    """Sync block timing. Emits a start line and a done line with elapsed."""
    stage(f"▶ {label}", **kwargs)
    t0 = time.monotonic()
    try:
        yield
    finally:
        stage(f"✓ {label}", elapsed=f"{time.monotonic() - t0:.2f}s")


@asynccontextmanager
async def atimed(label: str, **kwargs):
    """Async-aware block timing. Use with `async with atimed(...)`."""
    stage(f"▶ {label}", **kwargs)
    t0 = time.monotonic()
    try:
        yield
    finally:
        stage(f"✓ {label}", elapsed=f"{time.monotonic() - t0:.2f}s")


def setup_logging(level: int = logging.INFO) -> None:
    """Install a clean formatter and bump our demo logger's level.

    Called once from main.py's lifespan startup. Idempotent.
    Attaches a dedicated handler to the `tq` parent logger (so children like
    `tq.demo` inherit it) and disables propagation so uvicorn's default access
    formatter doesn't re-format our lines.
    """
    parent = logging.getLogger("tq")
    if not any(getattr(h, "_tq_demo_marker", False) for h in parent.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s.%(msecs)03d %(message)s", datefmt="%H:%M:%S")
        )
        handler._tq_demo_marker = True  # type: ignore[attr-defined]
        parent.addHandler(handler)

    parent.setLevel(level)
    parent.propagate = False
    log.setLevel(level)
