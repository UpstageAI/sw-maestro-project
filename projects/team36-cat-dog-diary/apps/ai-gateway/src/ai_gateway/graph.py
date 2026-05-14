"""LangGraph 조립.

토폴로지:
START → prepare_context → (cond: vision?) ┬─ no  → analyze_image ──┐
                                          └─ yes ──────────────────→ write_diary
                                                                       ↓
                                                                    safety_check
                                                                       ↓ (cond)
                                                              write_diary | END

vision/diary 책임 분리: analyze_image(agents/vision.py)가 사진 묘사 1단락을
state["vision_description"]에 채우면 write_diary(agents/diary.py)가 그 텍스트만
보고 작문. regenerate(seq>=2)에선 BFF가 직전 generation의 vision_description을
forward하면 prepare_context 다음 conditional edge가 analyze_image를 skip.
retry edge는 write_diary로만 돌아가 vision 재호출 없음.
"""
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from .agents.diary import safety_check, should_retry, write_diary
from .agents.vision import analyze_image
from .state import DiaryState


def prepare_context(state: DiaryState) -> dict:
    """Entry node. 입력 sanity 훅 — 현재 noop (Pydantic 검증으로 충분)."""
    return {}


def _route_vision(state: DiaryState) -> str:
    """conditional edge — vision_description 있으면 write_diary로 직접."""
    return "write_diary" if state.get("vision_description") else "analyze_image"


@lru_cache(maxsize=1)
def get_diary_graph() -> Any:
    builder: StateGraph = StateGraph(DiaryState)
    builder.add_node("prepare_context", prepare_context)
    builder.add_node("analyze_image", analyze_image)
    builder.add_node("write_diary", write_diary)
    builder.add_node("safety_check", safety_check)

    builder.add_edge(START, "prepare_context")
    builder.add_conditional_edges(
        "prepare_context",
        _route_vision,
        {"analyze_image": "analyze_image", "write_diary": "write_diary"},
    )
    builder.add_edge("analyze_image", "write_diary")
    builder.add_edge("write_diary", "safety_check")
    builder.add_conditional_edges(
        "safety_check",
        should_retry,
        {"write_diary": "write_diary", END: END},
    )

    return builder.compile()
