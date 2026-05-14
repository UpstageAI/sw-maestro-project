from __future__ import annotations

import logging
import time

from langgraph.graph import END, StateGraph

from agent.agent1.graph import agent1_graph
from agent.agent2.graph import agent2_graph
from agent.agent3.graph import agent3_graph
from models.schema import AgentState

logger = logging.getLogger(__name__)


def _run_agent1(state: AgentState) -> dict:
    ticker = state.get("ticker", "?")
    logger.info("[pipeline] Agent1 start — ticker=%s", ticker)
    t = time.monotonic()
    result = agent1_graph.invoke(state)
    errors = result.get("errors", [])
    logger.info("[pipeline] Agent1 done — %.1fs errors=%s", time.monotonic() - t, errors)
    return {
        "collected_data": result.get("collected_data"),
        "errors": errors,
    }


def _run_agent2(state: AgentState) -> dict:
    logger.info("[pipeline] Agent2 start — filter_noise → generate_hypotheses → score")
    t = time.monotonic()
    result = agent2_graph.invoke(state)
    errors = result.get("errors", [])
    hypotheses = result.get("hypotheses") or []
    logger.info("[pipeline] Agent2 done — %.1fs hypotheses=%d errors=%s", time.monotonic() - t, len(hypotheses), errors)
    return {
        "collected_data": result.get("collected_data"),  # filter_noise may update this
        "hypotheses": hypotheses,
        "errors": errors,
    }


def _run_agent3(state: AgentState) -> dict:
    logger.info("[pipeline] Agent3 start — report generation")
    t = time.monotonic()
    result = agent3_graph.invoke(state)
    errors = result.get("errors", [])
    logger.info("[pipeline] Agent3 done — %.1fs errors=%s", time.monotonic() - t, errors)
    return {
        "report": result.get("report"),
        "errors": errors,
    }


def _route_after_agent1(state: AgentState) -> str:
    if state.get("errors"):
        return END
    return "agent2"


def _route_after_agent2(state: AgentState) -> str:
    if state.get("errors"):
        return END
    return "agent3"


def build_pipeline():
    workflow = StateGraph(AgentState)

    workflow.add_node("agent1", _run_agent1)
    workflow.add_node("agent2", _run_agent2)
    workflow.add_node("agent3", _run_agent3)

    workflow.set_entry_point("agent1")
    workflow.add_conditional_edges(
        "agent1",
        _route_after_agent1,
        {"agent2": "agent2", END: END},
    )
    workflow.add_conditional_edges(
        "agent2",
        _route_after_agent2,
        {"agent3": "agent3", END: END},
    )
    workflow.add_edge("agent3", END)

    return workflow.compile()


pipeline = build_pipeline()
