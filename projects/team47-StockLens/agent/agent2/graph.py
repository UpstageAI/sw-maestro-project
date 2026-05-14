from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.agent2.nodes.filter_noise import filter_noise_node
from agent.agent2.nodes.generate_hypotheses import generate_hypotheses_node
from agent.agent2.nodes.score_hypotheses import score_hypotheses_node
from models.schema import AgentState


def _route_after_hypotheses(state: AgentState) -> str:
    """가설 생성 실패(errors 존재) 시 조기 종료."""
    if state.get("errors"):
        return END
    return "score_hypotheses"


def build_agent2_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("filter_noise", filter_noise_node)
    workflow.add_node("generate_hypotheses", generate_hypotheses_node)
    workflow.add_node("score_hypotheses", score_hypotheses_node)

    workflow.set_entry_point("filter_noise")
    workflow.add_edge("filter_noise", "generate_hypotheses")
    workflow.add_conditional_edges(
        "generate_hypotheses",
        _route_after_hypotheses,
        {"score_hypotheses": "score_hypotheses", END: END},
    )
    workflow.add_edge("score_hypotheses", END)

    return workflow.compile()


agent2_graph = build_agent2_graph()
