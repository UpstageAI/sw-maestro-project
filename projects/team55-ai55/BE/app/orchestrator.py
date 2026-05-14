from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, TypedDict

from app.agents import priority_subgraph, risk_subgraph, schedule_subgraph
from app.agents.risk import prefetch_risk_soft_checks
from app.schemas import (
    AnalyzeMeta,
    AnalyzeOptions,
    AnalyzeResponse,
    LlmFallbacks,
    LlmCalls,
    ProjectSnapshot,
)
from app.services.hash import compute_snapshot_hash
from app.services.observability import log_agent_call


class SessionState(TypedDict, total=False):
    project_id: str
    snapshot: ProjectSnapshot
    options: AnalyzeOptions
    now: datetime
    started: float
    snapshot_hash: str
    priority: Any
    schedule: Any
    risk: Any
    agent_latencies_ms: dict[str, int]
    prefetched_soft_checks: Any
    prefetched_soft_checks_timeout: bool
    prefetched_soft_check_calls: int
    response: AnalyzeResponse


async def analyze_snapshot(
    *,
    project_id: str,
    snapshot: ProjectSnapshot,
    options: AnalyzeOptions,
    now: datetime,
) -> AnalyzeResponse:
    final = await SUPER_GRAPH.ainvoke(
        {
            "project_id": project_id,
            "snapshot": snapshot,
            "options": options,
            "now": now,
        }
    )
    return final["response"]


async def _normalize_node(state: SessionState) -> dict[str, Any]:
    return {
        "started": time.perf_counter(),
        "snapshot_hash": compute_snapshot_hash(state["snapshot"]),
        "agent_latencies_ms": {},
    }


async def _priority_node(state: SessionState) -> dict[str, Any]:
    priority_start = time.perf_counter()
    priority_state = await priority_subgraph.ainvoke(
        {
            "snapshot": state["snapshot"],
            "now": state["now"],
            "request_decomposition_for": state["options"].request_decomposition_for,
            "use_llm": state["options"].use_llm,
        }
    )
    priority = priority_state["priority"]
    priority_ms = round((time.perf_counter() - priority_start) * 1000)
    latencies = {**state.get("agent_latencies_ms", {}), "priority": priority_ms}
    log_agent_call(
        project_id=state["project_id"],
        snapshot_hash=state["snapshot_hash"],
        agent="priority",
        latency_ms=priority_ms,
        schema_pass=True,
        retry_count=priority.agent_meta.schema_retries,
    )
    return {"priority": priority, "agent_latencies_ms": latencies}


async def _schedule_node(state: SessionState) -> dict[str, Any]:
    schedule_start = time.perf_counter()
    schedule_state = await schedule_subgraph.ainvoke(
        {
            "snapshot": state["snapshot"],
            "priority": state["priority"],
            "now": state["now"],
            "horizon_days": state["options"].schedule_horizon_days,
            "use_llm": state["options"].use_llm,
        }
    )
    schedule = schedule_state["schedule"]
    schedule_ms = round((time.perf_counter() - schedule_start) * 1000)
    latencies = {**state.get("agent_latencies_ms", {}), "schedule": schedule_ms}
    log_agent_call(
        project_id=state["project_id"],
        snapshot_hash=state["snapshot_hash"],
        agent="schedule",
        latency_ms=schedule_ms,
        schema_pass=True,
        retry_count=0,
    )
    return {"schedule": schedule, "agent_latencies_ms": latencies}


async def _schedule_and_risk_soft_node(state: SessionState) -> dict[str, Any]:
    schedule_task = asyncio.create_task(_schedule_node(state))
    soft_task = asyncio.create_task(prefetch_risk_soft_checks(state["snapshot"], use_llm=state["options"].use_llm))
    schedule_update, soft_result = await asyncio.gather(schedule_task, soft_task)
    soft_checks, soft_checks_timeout, soft_check_calls = soft_result
    return {
        **schedule_update,
        "prefetched_soft_checks": soft_checks,
        "prefetched_soft_checks_timeout": soft_checks_timeout,
        "prefetched_soft_check_calls": soft_check_calls,
    }


async def _risk_node(state: SessionState) -> dict[str, Any]:
    risk_start = time.perf_counter()
    risk_state = await risk_subgraph.ainvoke(
        {
            "snapshot": state["snapshot"],
            "priority": state["priority"],
            "schedule": state["schedule"],
            "now": state["now"],
            "use_llm": state["options"].use_llm,
            "prefetched_soft_checks": state.get("prefetched_soft_checks"),
            "prefetched_soft_checks_timeout": state.get("prefetched_soft_checks_timeout", False),
            "prefetched_soft_check_calls": state.get("prefetched_soft_check_calls"),
        }
    )
    risk = risk_state["risk"]
    risk_ms = round((time.perf_counter() - risk_start) * 1000)
    latencies = {**state.get("agent_latencies_ms", {}), "risk": risk_ms}
    log_agent_call(
        project_id=state["project_id"],
        snapshot_hash=state["snapshot_hash"],
        agent="risk",
        latency_ms=risk_ms,
        schema_pass=True,
        retry_count=0,
    )
    return {"risk": risk, "agent_latencies_ms": latencies}


async def _pack_response_node(state: SessionState) -> dict[str, Any]:
    priority = state["priority"]
    schedule_meta = getattr(state["schedule"], "_agent_meta", {})
    risk_meta = getattr(state["risk"], "_agent_meta", {})
    priority_narrator_fallback = "narrator_fallback_template" in priority.warnings
    risk_narrator_fallback = bool(risk_meta.get("narrator_fallback_template"))
    llm_calls = LlmCalls(
        priority_decompose=priority.agent_meta.decomposition_calls,
        priority_narrate=priority.agent_meta.narrator_calls,
        schedule_rerank=schedule_meta.get("rerank_calls", 0),
        risk_soft_checks=risk_meta.get("soft_check_calls", 0),
        risk_narrate=risk_meta.get("narrator_calls", 0),
    )
    llm_calls.total = (
        llm_calls.priority_decompose
        + llm_calls.priority_narrate
        + llm_calls.schedule_rerank
        + llm_calls.risk_soft_checks
        + llm_calls.risk_narrate
    )
    response = AnalyzeResponse(
        project_id=state["project_id"],
        snapshot_hash=state["snapshot_hash"],
        priority=priority,
        schedule=state["schedule"],
        risk=state["risk"],
        meta=AnalyzeMeta(
            latency_ms=round((time.perf_counter() - state["started"]) * 1000),
            agent_latencies_ms=state["agent_latencies_ms"],
            cache_hit=False,
            llm_calls=llm_calls,
            llm_fallbacks=LlmFallbacks(
                schedule_rerank_violation=any(
                    warning.startswith("rerank_violation:") or warning == "schedule_rerank_timeout"
                    for warning in state["schedule"].warnings
                ),
                risk_soft_checks_timeout=bool(risk_meta.get("soft_checks_timeout")),
                narrator_fallback_template=priority_narrator_fallback or risk_narrator_fallback,
                priority_narrator_fallback=priority_narrator_fallback,
                risk_narrator_fallback=risk_narrator_fallback,
            ),
        ),
    )
    log_agent_call(
        project_id=state["project_id"],
        snapshot_hash=state["snapshot_hash"],
        agent="super",
        latency_ms=response.meta.latency_ms,
        schema_pass=True,
        retry_count=0,
        extra={"llm_calls_total": llm_calls.total},
    )
    return {"response": response}


class _SequentialGraph:
    async def ainvoke(self, state: SessionState) -> SessionState:
        for node in (_normalize_node, _priority_node, _schedule_and_risk_soft_node, _risk_node, _pack_response_node):
            state.update(await node(state))
        return state


def _build_super_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ModuleNotFoundError:
        return _SequentialGraph()

    graph = StateGraph(SessionState)
    graph.add_node("normalize", _normalize_node)
    graph.add_node("priority", _priority_node)
    graph.add_node("schedule_and_risk_soft", _schedule_and_risk_soft_node)
    graph.add_node("risk", _risk_node)
    graph.add_node("pack_response", _pack_response_node)
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "priority")
    graph.add_edge("priority", "schedule_and_risk_soft")
    graph.add_edge("schedule_and_risk_soft", "risk")
    graph.add_edge("risk", "pack_response")
    graph.add_edge("pack_response", END)
    return graph.compile()


SUPER_GRAPH = _build_super_graph()
