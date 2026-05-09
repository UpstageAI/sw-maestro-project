"""Minimal HTTP interface for AI run orchestration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from autocoin_ai.app import AutocoinAgentApp


class ResumeRunRequest(BaseModel):
    run_id: str
    resume_reason: str
    patch_fields: dict[str, Any]


class CompleteRunRequest(BaseModel):
    run_id: str
    completion_payload: dict[str, Any]


class AgentStateResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent_app = AutocoinAgentApp()
    yield


app = FastAPI(title="autocoin-ai", lifespan=lifespan)


def get_agent_app(request: Request) -> AutocoinAgentApp:
    return request.app.state.agent_app


def map_value_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    if message.startswith("unknown run_id"):
        return HTTPException(status_code=404, detail=message)
    return HTTPException(status_code=400, detail=message)


@app.post("/runs/start", response_model=AgentStateResponse)
def start_run(state: dict[str, Any], request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.start(state))
    except ValueError as exc:
        raise map_value_error(exc) from exc


@app.post("/runs/resume", response_model=AgentStateResponse)
def resume_run(payload: ResumeRunRequest, request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.resume(payload.run_id, payload.patch_fields, payload.resume_reason))
    except ValueError as exc:
        raise map_value_error(exc) from exc


@app.post("/runs/complete", response_model=AgentStateResponse)
def complete_run(payload: CompleteRunRequest, request: Request) -> dict[str, Any]:
    agent_app = get_agent_app(request)
    try:
        return dict(agent_app.complete(payload.run_id, payload.completion_payload))
    except ValueError as exc:
        raise map_value_error(exc) from exc
