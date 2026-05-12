from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    candidate_node,
    create_job_node,
    criteria_node,
    help_node,
    restart_node,
    results_node,
    route_by_stage,
    router_node,
)
from app.agent.state import ChatState
from app.config import get_settings

_compiled = None


def build_graph() -> StateGraph:
    g = StateGraph(ChatState)
    g.add_node("router", router_node)
    g.add_node("create_job", create_job_node)
    g.add_node("criteria", criteria_node)
    g.add_node("candidate", candidate_node)
    g.add_node("results", results_node)
    g.add_node("help", help_node)
    g.add_node("restart", restart_node)

    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router",
        route_by_stage,
        {
            "create_job": "create_job",
            "criteria": "criteria",
            "candidate": "candidate",
            "results": "results",
            "help": "help",
            "restart": "restart",
        },
    )
    for node in ("create_job", "criteria", "candidate", "results", "help", "restart"):
        g.add_edge(node, END)
    return g


def get_compiled_graph():
    global _compiled
    if _compiled is None:
        settings = get_settings()
        ckpt_path = settings.artifacts_dir / "chat_checkpoints.sqlite"
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(ckpt_path), check_same_thread=False)
        saver = SqliteSaver(conn)
        _compiled = build_graph().compile(checkpointer=saver)
    return _compiled
