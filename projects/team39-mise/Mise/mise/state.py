"""Streamlit session_state 키 명세 및 헬퍼.

D 단계(인터랙션 UI) 컴포넌트들이 공유하는 session_state 스키마를 한 곳에서 정의한다.
C 단계(메인 UI)와 통합할 때 이 모듈만 import 하면 키 이름 충돌이 없다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import streamlit as st

from mise.models.scene_schema import PromptResult, SceneElements, SceneSchema

REGEN_LIMIT = 5
HISTORY_LIMIT = 5

STYLE_PRESETS: dict[str, str] = {
    "시네마틱": "cinematic",
    "수채화": "watercolor painting",
    "픽셀아트": "pixel art",
    "웹툰풍": "webtoon style",
}
DEFAULT_STYLE_LABEL = "시네마틱"


@dataclass
class HistoryItem:
    """이미지 히스토리 1건.

    image_bytes는 PIL.Image 직렬화 결과(PNG bytes). Streamlit 재실행에도 안전하게 보관 가능.
    """
    novel_text: str
    elements: dict[str, Any]
    prompt: dict[str, Any]
    style_label: str
    image_bytes: Optional[bytes]
    mode: str
    created_at: datetime = field(default_factory=datetime.now)


class Keys:
    """session_state 키 이름 상수. 다른 모듈에서 문자열 오타 방지용."""
    CURRENT_SCENE = "d_current_scene"
    EDITED_ELEMENTS = "d_edited_elements"
    STYLE_LABEL = "d_style_label"
    REGEN_COUNT = "d_regen_count"
    HISTORY = "d_history"
    SELECTED_HISTORY_IDX = "d_selected_history_idx"
    NOVEL_TEXT = "d_novel_text"


def init_state() -> None:
    """session_state 키들을 한 번만 초기화한다. 모든 D 컴포넌트 진입점에서 호출."""
    defaults: dict[str, Any] = {
        Keys.CURRENT_SCENE: None,
        Keys.EDITED_ELEMENTS: None,
        Keys.STYLE_LABEL: DEFAULT_STYLE_LABEL,
        Keys.REGEN_COUNT: 0,
        Keys.HISTORY: [],
        Keys.SELECTED_HISTORY_IDX: None,
        Keys.NOVEL_TEXT: "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_current_scene(scene: SceneSchema, novel_text: str) -> None:
    """새 SceneSchema가 도착하면 호출. 편집 버퍼도 함께 리셋."""
    st.session_state[Keys.CURRENT_SCENE] = scene
    st.session_state[Keys.EDITED_ELEMENTS] = scene.elements.model_dump()
    st.session_state[Keys.NOVEL_TEXT] = novel_text


def get_edited_elements() -> Optional[dict[str, Any]]:
    return st.session_state.get(Keys.EDITED_ELEMENTS)


def update_edited_field(field_name: str, value: Any) -> None:
    edited = st.session_state.get(Keys.EDITED_ELEMENTS) or {}
    edited[field_name] = value
    st.session_state[Keys.EDITED_ELEMENTS] = edited


def is_dirty() -> bool:
    """편집 버퍼가 current_scene과 달라졌는지."""
    scene: Optional[SceneSchema] = st.session_state.get(Keys.CURRENT_SCENE)
    edited: Optional[dict[str, Any]] = st.session_state.get(Keys.EDITED_ELEMENTS)
    if scene is None or edited is None:
        return False
    return scene.elements.model_dump() != edited


def can_regenerate() -> bool:
    return st.session_state.get(Keys.REGEN_COUNT, 0) < REGEN_LIMIT


def increment_regen() -> None:
    st.session_state[Keys.REGEN_COUNT] = st.session_state.get(Keys.REGEN_COUNT, 0) + 1


def reset_regen_count() -> None:
    """새 소설 텍스트로 generate 모드 호출 시 카운터 초기화."""
    st.session_state[Keys.REGEN_COUNT] = 0


def append_history(item: HistoryItem) -> None:
    """가장 최근이 인덱스 0이 되도록 prepend. HISTORY_LIMIT 초과 시 잘라낸다."""
    history: list[HistoryItem] = st.session_state.get(Keys.HISTORY, [])
    history.insert(0, item)
    st.session_state[Keys.HISTORY] = history[:HISTORY_LIMIT]


def get_history() -> list[HistoryItem]:
    return st.session_state.get(Keys.HISTORY, [])


def select_history(idx: Optional[int]) -> None:
    st.session_state[Keys.SELECTED_HISTORY_IDX] = idx


def get_selected_history() -> Optional[HistoryItem]:
    idx = st.session_state.get(Keys.SELECTED_HISTORY_IDX)
    history = get_history()
    if idx is None or idx >= len(history):
        return None
    return history[idx]


def build_prev_scene_payload() -> Optional[dict[str, Any]]:
    """regenerate 모드로 extract_scene을 호출할 때 넘길 prev_scene dict.

    편집된 요소 + 기존 source_type + 현재 prompt를 묶는다.
    """
    scene: Optional[SceneSchema] = st.session_state.get(Keys.CURRENT_SCENE)
    edited = st.session_state.get(Keys.EDITED_ELEMENTS)
    if scene is None or edited is None:
        return None
    return {
        "elements": edited,
        "source_type": scene.source_type,
        "prompt": scene.prompt.model_dump(),
    }


def get_style_value() -> str:
    """현재 선택된 스타일의 영문 키워드 값."""
    label = st.session_state.get(Keys.STYLE_LABEL, DEFAULT_STYLE_LABEL)
    return STYLE_PRESETS.get(label, "cinematic")
