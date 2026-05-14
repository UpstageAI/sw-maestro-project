"""Main graph builder — 1 review = 1 invocation.

START → load_context → pii_mask → classifier
      → [route_by_sentiment]
        ├→ thanks_drafter
        ├→ apology_drafter
        ├→ apology_drafter_lowconf
        ├→ neutral_drafter
        └→ noop_drafter        (P0-2 classification_failed / P0-3 lang_skip)
      → memory_save → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.graph.nodes.classifier import classifier_node
from src.graph.nodes.drafters import (
    apology_drafter,
    apology_drafter_lowconf,
    neutral_drafter,
    noop_drafter,
    thanks_drafter,
)
from src.graph.nodes.load_context import load_context_node
from src.graph.nodes.memory_save import memory_save_node
from src.graph.nodes.pii_mask import pii_mask_node
from src.graph.routes.sentiment import route_by_sentiment
from src.graph.state import ReviewState


def build_graph():
    g = StateGraph(ReviewState)

    # Nodes
    g.add_node("load_context", load_context_node)
    g.add_node("pii_mask", pii_mask_node)
    g.add_node("classifier", classifier_node)
    g.add_node("thanks_drafter", thanks_drafter)
    g.add_node("apology_drafter", apology_drafter)
    g.add_node("apology_drafter_lowconf", apology_drafter_lowconf)
    g.add_node("neutral_drafter", neutral_drafter)
    g.add_node("noop_drafter", noop_drafter)
    g.add_node("memory_save", memory_save_node)

    # Edges — linear up to classifier
    g.add_edge(START, "load_context")
    g.add_edge("load_context", "pii_mask")
    g.add_edge("pii_mask", "classifier")

    # Conditional edge — Router (LangGraph surface 1 of 4)
    g.add_conditional_edges(
        "classifier",
        route_by_sentiment,
        {
            "thanks_drafter": "thanks_drafter",
            "apology_drafter": "apology_drafter",
            "apology_drafter_lowconf": "apology_drafter_lowconf",
            "neutral_drafter": "neutral_drafter",
            "noop_drafter": "noop_drafter",
        },
    )

    # Drafter → memory_save
    for drafter_name in (
        "thanks_drafter",
        "apology_drafter",
        "apology_drafter_lowconf",
        "neutral_drafter",
        "noop_drafter",
    ):
        g.add_edge(drafter_name, "memory_save")

    g.add_edge("memory_save", END)

    return g.compile()


# 모듈 import 시 1회 컴파일
graph = build_graph()
