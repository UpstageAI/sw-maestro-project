"""LangGraph 워크플로우.

plan → write → critique → (조건부) → write 또는 finalize → END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.graph.state import GraphState
from app.graph.nodes import (
    plan, write, critique, finalize, route_after_critique,
)


def build_graph():
    g = StateGraph(GraphState)

    g.add_node("plan", plan)
    g.add_node("write", write)
    g.add_node("critique", critique)
    g.add_node("finalize", finalize)

    g.set_entry_point("plan")
    g.add_edge("plan", "write")
    g.add_edge("write", "critique")
    g.add_conditional_edges(
        "critique",
        route_after_critique,
        {"write": "write", "finalize": "finalize"},
    )
    g.add_edge("finalize", END)

    return g.compile()


graph = build_graph()
