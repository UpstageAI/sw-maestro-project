from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.agent3.nodes.generate_report import generate_report_node
from agent.agent3.nodes.save_to_db import save_to_db_node
from models.schema import AgentState


def _route_after_report(state: AgentState) -> str:
    """보고서 생성 실패(errors 존재) 시 DB 저장 건너뜀."""
    if state.get("errors"):
        return END
    return "save_to_db"


def build_agent3_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("save_to_db", save_to_db_node)

    workflow.set_entry_point("generate_report")
    workflow.add_conditional_edges(
        "generate_report",
        _route_after_report,
        {"save_to_db": "save_to_db", END: END},
    )
    workflow.add_edge("save_to_db", END)

    return workflow.compile()


agent3_graph = build_agent3_graph()
