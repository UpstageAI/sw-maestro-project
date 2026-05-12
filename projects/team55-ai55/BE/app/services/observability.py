from __future__ import annotations

import json
import logging
from typing import Any

import structlog


def _json_dumps(value: Any, **_: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


structlog.configure(
    processors=[structlog.processors.JSONRenderer(serializer=_json_dumps)],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.getLogger("app.observability").setLevel(logging.INFO)
logger = structlog.get_logger("app.observability")


def log_agent_call(
    *,
    project_id: str,
    snapshot_hash: str,
    agent: str,
    latency_ms: int,
    cache_hit: bool = False,
    schema_pass: bool | None = None,
    retry_count: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "project_id": project_id,
        "snapshot_hash": snapshot_hash,
        "agent": agent,
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "schema_pass": schema_pass,
        "retry_count": retry_count,
        "cache_hit": cache_hit,
    }
    if extra:
        payload.update(extra)
    logger.info("agent_call", **payload)
