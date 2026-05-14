"""Conditional Edge — Node B 분기 함수 (PRD US-013 / FR-9 / FR-16 / §7.7)."""
from __future__ import annotations

from typing import Literal

from graph.state import LaptopChatState

MAX_TURNS = 20


def route_after_b(state: LaptopChatState) -> Literal["complete", "incomplete"]:
    if int(state.get("turn_count") or 0) > MAX_TURNS:
        return "complete"
    return "complete" if state.get("is_complete") else "incomplete"
