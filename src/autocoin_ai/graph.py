"""LangGraph assembly for the standalone AI Agent."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_HOLD
from autocoin_ai.models import AgentState
from autocoin_ai.nodes.evaluator import evaluator_node
from autocoin_ai.nodes.execution import execution_node
from autocoin_ai.nodes.intake import intake_node
from autocoin_ai.nodes.policy import policy_node
from autocoin_ai.nodes.risk import risk_node
from autocoin_ai.nodes.risk_agent import risk_agent_node
from autocoin_ai.nodes.risk_gate import risk_gate_node
from autocoin_ai.nodes.strategy import strategy_node


def route_after_policy(state: AgentState) -> str:
    if state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return END
    return "risk"


def route_after_risk(state: AgentState) -> str:
    if state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return END
    return "evaluator"


# --- Agentic graph routing (§10.2) ---

def route_after_intake(state: AgentState) -> str:
    lc = state.get("lifecycle_status")
    if lc == LIFECYCLE_FAILED:
        return END
    if lc == LIFECYCLE_HOLD:
        return "evaluator"
    return "policy"


def route_after_agentic_policy(state: AgentState) -> str:
    if state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return END
    return "strategy"


def route_after_strategy(state: AgentState) -> str:
    if state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return END
    return "risk_agent"


def build_agentic_order_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("intake", intake_node)
    graph.add_node("policy", policy_node)
    graph.add_node("strategy", strategy_node)
    graph.add_node("risk_agent", risk_agent_node)
    graph.add_node("risk_gate", risk_gate_node)
    graph.add_node("evaluator", evaluator_node)
    graph.set_entry_point("intake")
    graph.add_conditional_edges("intake", route_after_intake)
    graph.add_conditional_edges("policy", route_after_agentic_policy)
    graph.add_conditional_edges("strategy", route_after_strategy)
    graph.add_edge("risk_agent", "risk_gate")
    graph.add_edge("risk_gate", "evaluator")
    graph.add_edge("evaluator", END)
    return graph.compile(checkpointer=MemorySaver())


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
