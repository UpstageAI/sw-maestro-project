"""load_context node — Memory Store에서 매장 메타·톤 샘플·피드백 hint를 읽어 state에 주입."""

from __future__ import annotations

import os

from src.graph.trace import measure
from src.store import memory

TONE_LIMIT = int(os.getenv("TONE_SAMPLES_LIMIT", "3"))


def load_context_node(state: dict) -> dict:
    place_id = state["place_id"]
    with measure("load_context", "memory_read") as log:
        metadata = memory.get_metadata(place_id)
        tone_samples = memory.get_tone_samples(place_id, limit=TONE_LIMIT)
        feedback_hints = memory.get_feedback_hints(place_id, limit=5)

        log["summary"] = (
            f"메타 1 · 톤샘플 {len(tone_samples)} · 피드백 {len(feedback_hints)}"
        )
        log["details"] = {
            "namespaces_read": [
                f"({place_id}, 'metadata')",
                f"({place_id}, 'tone_samples')",
                f"({place_id}, 'feedback')",
            ],
            "place_id": place_id,
            "tone_samples_count": len(tone_samples),
            "feedback_hints_count": len(feedback_hints),
            "menus_count": len(metadata.get("menus", [])),
            "tone_preference": metadata.get("tone_preference"),
        }

    return {
        "place_metadata": metadata,
        "tone_samples": tone_samples,
        "feedback_hints": feedback_hints,
        "node_log": [log],
    }
