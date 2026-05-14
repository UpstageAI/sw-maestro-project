"""LangGraph State 스키마 (PRD US-006 / §7.1 / §7.7).

`TypedDict` 기반 — `messages` 만 `add_messages` reducer 로 자동 누적,
`slots` 외 나머지 필드는 단순 덮어쓰기.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

SLOT_KEYS: tuple[str, ...] = (
    "screen_inch",
    "weight_kg",
    "os",
    "resolution",
    "brightness_nits",
    "cpu",
    "ram_gb",
    "storage_gb",
    "price_krw",
)


class Slots(TypedDict, total=False):
    screen_inch: Optional[float]
    weight_kg: Optional[float]
    os: Optional[str]
    resolution: Optional[str]
    brightness_nits: Optional[int]
    cpu: Optional[str]
    ram_gb: Optional[int]
    storage_gb: Optional[int]
    price_krw: Optional[int]


class SlotOption(TypedDict, total=False):
    value: Any
    label: str
    rationale: str


class LaptopChatState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    slots: Slots
    use_case: Optional[str]
    slot_options: dict[str, list[SlotOption]]
    inferred_keys: list[str]
    last_assistant_question: Optional[str]
    sql_clause: Optional[tuple[str, list[Any]]]
    candidates: list[dict[str, Any]]
    final_answer: Optional[str]
    turn_count: int
    is_complete: bool


def empty_slots() -> Slots:
    return {k: None for k in SLOT_KEYS}  # type: ignore[return-value]


def initial_state() -> LaptopChatState:
    return {
        "messages": [],
        "slots": empty_slots(),
        "use_case": None,
        "slot_options": {},
        "inferred_keys": [],
        "last_assistant_question": None,
        "sql_clause": None,
        "candidates": [],
        "final_answer": None,
        "turn_count": 0,
        "is_complete": False,
    }


def compute_is_complete(slots: Slots) -> bool:
    return all(slots.get(k) is not None for k in SLOT_KEYS)


def filled_count(slots: Slots) -> int:
    return sum(1 for k in SLOT_KEYS if slots.get(k) is not None)


def missing_keys(slots: Slots) -> list[str]:
    return [k for k in SLOT_KEYS if slots.get(k) is None]
