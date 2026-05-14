"""LangGraph wiring for agents 2-6.

Agent 1 (input validation) runs synchronously in the request handler before
the graph is invoked — this mirrors the original TS pipeline which short-
circuits with a 400 response on validation failure.

Each node writes its own ``agent_start`` / ``agent_done`` (and the final node
writes ``pipeline_done``) via ``get_stream_writer``. Consumers iterate the
graph with ``stream_mode='custom'`` to receive these events.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from _lib.agents.destination_retrieval import destination_retrieval_node
from _lib.agents.ranking import ranking_node
from _lib.agents.response_generation import response_generation_node
from _lib.agents.saju_analysis import saju_analysis_node
from _lib.agents.travel_style_mapping import travel_style_mapping_node
from _lib.state import AgentState


def _build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("saju-analysis", saju_analysis_node)
    graph.add_node("travel-style-mapping", travel_style_mapping_node)
    graph.add_node("destination-retrieval", destination_retrieval_node)
    graph.add_node("ranking", ranking_node)
    graph.add_node("response-generation", response_generation_node)

    graph.add_edge(START, "saju-analysis")
    graph.add_edge("saju-analysis", "travel-style-mapping")
    graph.add_edge("travel-style-mapping", "destination-retrieval")
    graph.add_edge("destination-retrieval", "ranking")
    graph.add_edge("ranking", "response-generation")
    graph.add_edge("response-generation", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Compile lazily and reuse across invocations within the warm Fluid Compute
    instance.
    """
    return _build_graph()
