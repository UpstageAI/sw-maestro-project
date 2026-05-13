from __future__ import annotations

from datetime import datetime
from typing import Any

from src.state import ReviewAgentState


def append_backend_log(
    state: ReviewAgentState,
    *,
    node_name: str,
    input_summary: str,
    output_summary: str,
    db_saved: bool,
    has_warning: bool = False,
    has_error: bool = False,
) -> None:
    state.backend_logs.append(
        {
            "node_name": node_name,
            "executed_at": datetime.now().isoformat(timespec="seconds"),
            "input_summary": input_summary,
            "output_summary": output_summary,
            "db_saved": db_saved,
            "has_warning": has_warning,
            "has_error": has_error,
        }
    )


def summarize_counts(items: list[Any], *, noun: str) -> str:
    return f"{len(items)}{noun}"
