"""LangGraph assembly for the standalone AI Agent."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_READY_FOR_BE
from autocoin_ai.models import AgentState
from autocoin_ai.nodes.evaluator import evaluator_node
from autocoin_ai.nodes.execution import execution_node
from autocoin_ai.nodes.policy import policy_node
from autocoin_ai.nodes.risk import risk_node


def route_after_policy(state: AgentState) -> str:
    if state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return END
    return "risk"


def route_after_risk(state: AgentState) -> str:
    if state.get("lifecycle_status") == LIFECYCLE_READY_FOR_BE:
        return "evaluator"
    return END


def build_order_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("policy", policy_node)
    graph.add_node("risk", risk_node)
    graph.add_node("evaluator", evaluator_node)
    graph.set_entry_point("policy")
    graph.add_conditional_edges("policy", route_after_policy)
    graph.add_conditional_edges("risk", route_after_risk)
    graph.add_edge("evaluator", END)
    return graph.compile(checkpointer=MemorySaver())


def build_completion_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("execution", execution_node)
    graph.set_entry_point("execution")
    graph.add_edge("execution", END)
    return graph.compile(checkpointer=MemorySaver())


def draw_order_graph_mermaid() -> str:
    return build_order_graph().get_graph().draw_mermaid()


def draw_completion_graph_mermaid() -> str:
    return build_completion_graph().get_graph().draw_mermaid()
