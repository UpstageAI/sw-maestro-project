import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


async def start_run(
    run_id: str,
    request_context: dict[str, Any],
    policy_context: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "run_id": run_id,
        "request_context": request_context,
        "policy_context": policy_context,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.ai_service_http_url}/runs/start",
            json=state,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def resume_run(
    run_id: str,
    resume_reason: str,
    patch_fields: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "resume_reason": resume_reason,
        "patch_fields": patch_fields,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.ai_service_http_url}/runs/resume",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def send_completion(
    run_id: str,
    completion_payload: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "completion_payload": completion_payload,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.ai_service_http_url}/runs/complete",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
