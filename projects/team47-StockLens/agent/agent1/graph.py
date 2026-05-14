from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.agent1.nodes.collect_benchmark import collect_benchmark_node
from agent.agent1.nodes.collect_news_filings import collect_news_filings_node
from agent.agent1.nodes.collect_price import collect_price_node
from models.schema import AgentState


def _route_after_price(state: AgentState) -> str:
    """주가 수집 실패(errors 존재) 시 조기 종료."""
    if state.get("errors"):
        return END
    return "collect_benchmark_data"


def build_agent1_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("collect_price_data", collect_price_node)
    workflow.add_node("collect_benchmark_data", collect_benchmark_node)
    workflow.add_node("collect_news_and_filings", collect_news_filings_node)

    workflow.set_entry_point("collect_price_data")
    workflow.add_conditional_edges(
        "collect_price_data",
        _route_after_price,
        {"collect_benchmark_data": "collect_benchmark_data", END: END},
    )
    workflow.add_edge("collect_benchmark_data", "collect_news_and_filings")
    workflow.add_edge("collect_news_and_filings", END)

    return workflow.compile()


agent1_graph = build_agent1_graph()
