"""Minimal HTTP interface for AI run orchestration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.run_store import JsonFileRunStore


class ResumeRunRequest(BaseModel):
    run_id: str
    resume_reason: str
    patch_fields: dict[str, Any]


class CompleteRunRequest(BaseModel):
    run_id: str
    completion_payload: dict[str, Any]


class StartRunRequest(BaseModel):
    run_id: str
    request_context: dict[str, Any]
    policy_context: dict[str, Any]


class AgentStateResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class CheckpointEvidenceResponse(BaseModel):
    final_snapshot_lifecycle_status: str | None
    history_snapshot_count: int


router = APIRouter()


def create_app(run_store: JsonFileRunStore | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent_app = AutocoinAgentApp(run_store=run_store or JsonFileRunStore.from_env())
        yield

    created_app = FastAPI(title="autocoin-ai", lifespan=lifespan)
    created_app.include_router(router)
    return created_app


def get_agent_app(request: Request) -> AutocoinAgentApp:
    return request.app.state.agent_app


def map_value_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    if message.startswith("unknown run_id"):
        return HTTPException(status_code=404, detail=message)
    return HTTPException(status_code=400, detail=message)


@router.post("/runs/start", response_model=AgentStateResponse)
def start_run(state: StartRunRequest, request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.start(state.model_dump()))
    except ValueError as exc:
        raise map_value_error(exc) from exc


@router.post("/runs/agentic/start", response_model=AgentStateResponse)
def start_agentic_run(state: StartRunRequest, request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.start_agentic(state.model_dump()))
    except ValueError as exc:
        raise map_value_error(exc) from exc


@router.post("/runs/resume", response_model=AgentStateResponse)
def resume_run(payload: ResumeRunRequest, request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.resume(payload.run_id, payload.patch_fields, payload.resume_reason))
    except ValueError as exc:
        raise map_value_error(exc) from exc


@router.post("/runs/complete", response_model=AgentStateResponse)
def complete_run(payload: CompleteRunRequest, request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.complete(payload.run_id, payload.completion_payload))
    except ValueError as exc:
        raise map_value_error(exc) from exc


@router.get("/runs/{run_id}/checkpoints/order", response_model=CheckpointEvidenceResponse)
def order_checkpoint(run_id: str, request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.order_checkpoint_evidence(run_id))
    except ValueError as exc:
        raise map_value_error(exc) from exc


@router.get("/runs/{run_id}/checkpoints/completion", response_model=CheckpointEvidenceResponse)
def completion_checkpoint(run_id: str, request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.completion_checkpoint_evidence(run_id))
    except ValueError as exc:
        raise map_value_error(exc) from exc


app = create_app()
