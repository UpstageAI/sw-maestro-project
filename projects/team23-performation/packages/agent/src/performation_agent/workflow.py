from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import lru_cache

from langgraph.graph import END, StateGraph

from performation_agent.nodes import (
  analyze_input,
  assign_confidence,
  build_search_queries,
  classify_sources,
  extract_event_info,
  format_response,
  infer_event_candidates,
  infer_venue_from_search,
  load_venue_data,
  search_kopis_official,
  search_public_web,
  summarize_information,
)
from performation_agent.state import GuideState
from performation_domain import GuideResponse


logger = logging.getLogger("performation.agent.workflow")

NODE_SEQUENCE = (
  "analyze_input",
  "load_venue_data",
  "build_search_queries",
  "search_public_web",
  "search_kopis_official",
  "infer_venue_from_search",
  "infer_event_candidates",
  "extract_event_info",
  "classify_sources",
  "summarize_information",
  "assign_confidence",
  "format_response",
)
NODE_STEPS = {
  node_name: f"{index:02d}/{len(NODE_SEQUENCE):02d}"
  for index, node_name in enumerate(NODE_SEQUENCE, start=1)
}


def generate_visit_guide(query: str) -> GuideResponse:
  state = build_workflow_graph().invoke({"query": query})
  return state["response"]


@lru_cache(maxsize=1)
def build_workflow_graph():
  graph = StateGraph(GuideState)
  graph.add_node("analyze_input", _logged_node("analyze_input", analyze_input))
  graph.add_node("load_venue_data", _logged_node("load_venue_data", load_venue_data))
  graph.add_node("build_search_queries", _logged_node("build_search_queries", build_search_queries))
  graph.add_node("search_public_web", _logged_node("search_public_web", search_public_web))
  graph.add_node("search_kopis_official", _logged_node("search_kopis_official", search_kopis_official))
  graph.add_node("infer_venue_from_search", _logged_node("infer_venue_from_search", infer_venue_from_search))
  graph.add_node("infer_event_candidates", _logged_node("infer_event_candidates", infer_event_candidates))
  graph.add_node("extract_event_info", _logged_node("extract_event_info", extract_event_info))
  graph.add_node("classify_sources", _logged_node("classify_sources", classify_sources))
  graph.add_node("summarize_information", _logged_node("summarize_information", summarize_information))
  graph.add_node("assign_confidence", _logged_node("assign_confidence", assign_confidence))
  graph.add_node("format_response", _logged_node("format_response", format_response))

  graph.set_entry_point("analyze_input")
  for current_node, next_node in zip(NODE_SEQUENCE, NODE_SEQUENCE[1:]):
    graph.add_edge(current_node, next_node)
  graph.add_edge("format_response", END)

  return graph.compile()


def _logged_node(
  node_name: str,
  node: Callable[[GuideState], GuideState],
) -> Callable[[GuideState], GuideState]:
  def wrapped(state: GuideState) -> GuideState:
    step = NODE_STEPS[node_name]
    if logger.isEnabledFor(logging.INFO):
      logger.info("[workflow %s] START %-24s", step, node_name)
    started = time.monotonic()
    try:
      update = node(state)
    except Exception:
      elapsed = time.monotonic() - started
      logger.exception("[workflow %s] FAIL  %-24s elapsed=%.2fs", step, node_name, elapsed)
      raise

    elapsed = time.monotonic() - started
    if logger.isEnabledFor(logging.INFO):
      merged_state = {**state, **update}
      logger.info(
        "[workflow %s] DONE  %-24s elapsed=%.2fs changes=%s | %s",
        step,
        node_name,
        elapsed,
        _state_changes_summary(state, merged_state),
        _state_log_summary(merged_state),
      )
    return update

  return wrapped


def _state_log_summary(state: GuideState) -> str:
  snapshot = _state_log_snapshot(state)
  return (
    f"state: intent={snapshot['intent']} | type={snapshot['input_type']} | venue={snapshot['venue']} | "
    f"search={snapshot['search_queries']}q/{snapshot['search_results']}r | "
    f"event={snapshot['event_info']}/{snapshot['event_candidates']}c | "
    f"guide={snapshot['summary']}s/{snapshot['checklist']}c/{snapshot['transit_tips']}t/"
    f"{snapshot['official_checks']}o | sources={snapshot['sources']} | "
    f"fallback={snapshot['fallback_used']} | llm={snapshot['llm_used']} | "
    f"response={snapshot['response_ready']}"
  )


def _state_changes_summary(before: GuideState, after: GuideState) -> str:
  before_snapshot = _state_log_snapshot(before)
  after_snapshot = _state_log_snapshot(after)
  changes = [
    f"{key}:{before_snapshot[key]}->{after_snapshot[key]}"
    for key in after_snapshot
    if before_snapshot[key] != after_snapshot[key]
  ]
  if not changes:
    return "none"
  return ",".join(changes)


def _state_log_snapshot(state: GuideState) -> dict[str, str | int | bool]:
  venue = state.get("venue")
  event_info = state.get("event_info")
  response = state.get("response")
  return {
    "intent": state.get("input_intent", "pending"),
    "input_type": state.get("input_type", "pending"),
    "venue": venue.name if venue else "none",
    "search_queries": len(state.get("search_queries", [])),
    "search_results": len(state.get("search_results", [])),
    "event_info": "yes" if event_info else "no",
    "event_candidates": len(state.get("event_candidates", [])),
    "summary": len(state.get("summary", [])),
    "checklist": len(state.get("checklist", [])),
    "transit_tips": len(state.get("transit_and_entry_tips", [])),
    "official_checks": len(state.get("official_check_required", [])),
    "sources": len(state.get("sources", [])),
    "fallback_used": state.get("fallback_used", False),
    "llm_used": state.get("llm_used", False),
    "response_ready": "yes" if response else "no",
  }
