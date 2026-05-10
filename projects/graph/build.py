"""LangGraph StateGraph 빌더 (PRD §7.7 — 단일 invoke = 1 턴)."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from graph.edges import route_after_b
from graph.nodes import (
    node_b_evaluate,
    node_c_followup,
    node_d_sql,
    node_e_query,
    node_f_answer,
)
from graph.state import LaptopChatState


def build_graph():
    g: StateGraph = StateGraph(LaptopChatState)
    g.add_node("B", node_b_evaluate)
    g.add_node("C", node_c_followup)
    g.add_node("D", node_d_sql)
    g.add_node("E", node_e_query)
    g.add_node("F", node_f_answer)

    g.set_entry_point("B")
    g.add_conditional_edges(
        "B",
        route_after_b,
        {"complete": "D", "incomplete": "C"},
    )
    g.add_edge("C", END)
    g.add_edge("D", "E")
    g.add_edge("E", "F")
    g.add_edge("F", END)

    return g.compile()
