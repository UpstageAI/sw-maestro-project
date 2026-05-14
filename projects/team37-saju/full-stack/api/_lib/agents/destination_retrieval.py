"""Agent 4 — Destination Retrieval (LangGraph node).

Filters and scores destinations against the user's range constraint, element
needs, and mapping preferences. Pure logic — no LLM call.
"""

from __future__ import annotations

from typing import Any, Dict, List

from langgraph.config import get_stream_writer

from _lib.destinations import SERVER_DESTINATIONS, CandidateDestination
from _lib.state import AgentState, make_event

RANGE_LIMITS: Dict[str, float] = {
    "2시간 이내": 2.0,
    "4시간 이내": 4.0,
    "제한 없음": 99.0,
}

MIN_CANDIDATES = 5


def _score_for(
    d: CandidateDestination,
    saju: Dict[str, Any],
    mapping: Dict[str, Any],
) -> float:
    element_hits = 2.0 if saju["needsBoost"] in d["elementAffinity"] else 0.0
    dominant_penalty = -0.3 if saju["elements"]["dominant"] in d["elementAffinity"] else 0.0
    preferred_tags = set(mapping["preferredTags"])
    tag_hits = sum(1 for t in d["tags"] if t in preferred_tags)
    target_styles = {mapping["primary"], mapping["secondary"]} - {None}
    style_hits = sum(1 for s in d["styles"] if s in target_styles)
    return element_hits + tag_hits * 0.7 + style_hits * 1.2 + dominant_penalty


async def destination_retrieval_node(state: AgentState) -> Dict[str, Any]:
    writer = get_stream_writer()
    writer(make_event(
        "agent_start", agent="destination-retrieval", index=3, total=6,
    ))

    user_input = state["userInput"]
    saju = state["saju"]
    mapping = state["mapping"]
    limit = RANGE_LIMITS[user_input["travelRange"]]

    in_range: List[CandidateDestination] = [
        d for d in SERVER_DESTINATIONS
        if d["travelTime"][user_input["departure"]] <= limit
    ]

    pool = in_range if len(in_range) >= MIN_CANDIDATES else SERVER_DESTINATIONS
    ranked = sorted(pool, key=lambda d: _score_for(d, saju, mapping), reverse=True)
    candidates = ranked[: min(7, len(ranked))]

    filter_stats = {
        "totalPool": len(SERVER_DESTINATIONS),
        "afterRangeFilter": len(in_range),
        "finalPool": len(candidates),
        "relaxedRange": len(in_range) < MIN_CANDIDATES,
    }

    writer(make_event(
        "agent_done", agent="destination-retrieval", index=3, total=6,
        payload={"count": len(candidates), "filterStats": filter_stats},
    ))

    return {"candidates": candidates, "filterStats": filter_stats}
