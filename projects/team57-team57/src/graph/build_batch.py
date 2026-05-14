"""Batch graph — 주1회 누적 분석 (Tool use surface 노출).

START → pattern_aggregator (SQL tool 호출) → checklist_generator → END
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src.graph.nodes.checklist import checklist_agent_node
from src.graph.nodes.pattern import pattern_agent_node
from src.store import memory


class BatchState(TypedDict, total=False):
    place_id: str
    place_metadata: dict
    top3_data: list[dict]
    top3_summary: str
    checklist: list[str]


def _load_meta_node(state: dict) -> dict:
    return {"place_metadata": memory.get_metadata(state["place_id"])}


def build_batch_graph():
    g = StateGraph(BatchState)
    g.add_node("load_meta", _load_meta_node)
    g.add_node("pattern_aggregator", pattern_agent_node)
    g.add_node("checklist_generator", checklist_agent_node)

    g.add_edge(START, "load_meta")
    g.add_edge("load_meta", "pattern_aggregator")
    g.add_edge("pattern_aggregator", "checklist_generator")
    g.add_edge("checklist_generator", END)

    return g.compile()


batch_graph = build_batch_graph()
