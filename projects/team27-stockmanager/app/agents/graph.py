from __future__ import annotations

import time
from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from .collector import collect
from .extractor import extract
from .reporter import write_report


class ReportState(TypedDict, total=False):
    symbol: str
    summary: dict
    context: str
    report: str
    trace: Annotated[list[dict], add]


def _step(name: str, status: str, t0: float, **info) -> dict:
    return {
        "step": name,
        "status": status,
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        "info": info,
    }


def _collect_node(state: ReportState) -> ReportState:
    t0 = time.perf_counter()
    summary = collect(state["symbol"])
    return {
        "summary": summary,
        "trace": [
            _step(
                "collector",
                "ok",
                t0,
                symbol=state["symbol"],
                n_chunks=summary.get("n_chunks", 0),
                n_bars=len(summary.get("bars", [])),
                data_source=summary.get("data_source"),
                fetch_status=summary.get("fetch_status", {}),
            )
        ],
    }


def _extract_node(state: ReportState) -> ReportState:
    t0 = time.perf_counter()
    ctx = extract(state["symbol"], k=12)
    return {
        "context": ctx,
        "trace": [
            _step(
                "extractor",
                "ok" if ctx else "empty",
                t0,
                symbol=state["symbol"],
                k=12,
                context_chars=len(ctx),
            )
        ],
    }


def _report_node(state: ReportState) -> ReportState:
    t0 = time.perf_counter()
    ctx = state.get("context", "")
    rep = write_report(state["symbol"], ctx)
    return {
        "report": rep,
        "trace": [
            _step(
                "reporter",
                "ok" if ctx.strip() else "no_context",
                t0,
                symbol=state["symbol"],
                report_chars=len(rep),
                llm_call=bool(ctx.strip()),
            )
        ],
    }


def build_report_graph():
    g = StateGraph(ReportState)
    g.add_node("collector", _collect_node)
    g.add_node("extractor", _extract_node)
    g.add_node("reporter", _report_node)
    g.set_entry_point("collector")
    g.add_edge("collector", "extractor")
    g.add_edge("extractor", "reporter")
    g.add_edge("reporter", END)
    return g.compile()


report_graph = build_report_graph()


def generate_report(symbol: str) -> dict:
    final = report_graph.invoke({"symbol": symbol, "trace": []})
    summary = final.get("summary", {})
    return {
        "symbol": symbol,
        "summary": summary,
        "report": final.get("report", ""),
        "data_source": summary.get("data_source", "live"),
        "fetch_status": summary.get("fetch_status", {}),
        "fallback_reason": summary.get("fallback_reason", ""),
        "kis_auth_mode": summary.get("kis_auth_mode", "client_credentials"),
        "kis_auth_ready": summary.get("kis_auth_ready", False),
        "trace": final.get("trace", []),
    }
