"""12개 장면 요소 카드 그리드. 사용자가 각 값을 직접 편집할 수 있다.

C 단계의 메인 화면에서는 분석 단계 직후 이 컴포넌트를 호출한다.
편집된 값은 mise.state.update_edited_field()로 자동 반영되어, 재생성 시 prev_scene으로 전달된다.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from mise.state import Keys, get_edited_elements, update_edited_field

ELEMENT_LABELS: list[tuple[str, str, str]] = [
    ("character", "인물", "외형, 복장, 자세"),
    ("background", "배경", "환경, 공간 구조"),
    ("time", "시간대", "새벽/오전/오후/저녁/밤"),
    ("place", "장소", "구체적 장소"),
    ("objects", "사물", "주요 사물 (콤마로 구분)"),
    ("action", "행동", "인물의 동작"),
    ("emotion", "감정", "감정 상태"),
    ("mood", "분위기", "전체 분위기"),
    ("color", "색감", "색조"),
    ("lighting", "조명", "조명 상태"),
    ("camera_view", "시점", "카메라 앵글"),
    ("composition", "구도", "화면 구도"),
]

LONG_FIELDS = {"character", "background", "mood"}


def _widget_key(field_key: str) -> str:
    return f"d_card_{field_key}"


def _to_widget_value(field_key: str, value: Any) -> str:
    if field_key == "objects":
        return ", ".join(value) if isinstance(value, list) else str(value or "")
    return str(value or "")


def _from_widget_value(field_key: str, text: str) -> Any:
    if field_key == "objects":
        return [item.strip() for item in text.split(",") if item.strip()]
    return text


def _render_field(field_key: str, label: str, helper: str) -> Any:
    """위젯은 session_state[widget_key]를 직접 읽고 쓴다.

    값 동기화는 sync_card_widgets()에서 미리 한다 (위젯 렌더링 후 session_state에 쓰면
    StreamlitAPIException이 발생하므로 분리).
    """
    widget_key = _widget_key(field_key)
    if field_key in LONG_FIELDS:
        text = st.text_area(label, key=widget_key, help=helper, height=80)
    else:
        text = st.text_input(label, key=widget_key, help=helper)
    return _from_widget_value(field_key, text)


def render_scene_cards(read_only: bool = False) -> None:
    """현재 편집 버퍼를 카드 그리드로 표시하고, 변경 사항을 session_state에 반영한다.

    Args:
        read_only: True면 값만 표시한다 (히스토리 미리보기 등에 사용).
    """
    edited = get_edited_elements()
    if edited is None:
        st.info("아직 분석된 장면이 없습니다. 텍스트를 입력하고 '시각화'를 눌러주세요.")
        return

    if not read_only:
        sync_card_widgets(edited)

    cols_per_row = 3
    for row_start in range(0, len(ELEMENT_LABELS), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, (field_key, label, helper) in zip(cols, ELEMENT_LABELS[row_start:row_start + cols_per_row]):
            with col:
                if read_only:
                    _render_readonly(field_key, label, edited.get(field_key))
                else:
                    new_value = _render_field(field_key, label, helper)
                    update_edited_field(field_key, new_value)


def _render_readonly(field_key: str, label: str, value: Any) -> None:
    if field_key == "objects" and isinstance(value, list):
        text = ", ".join(value) if value else "—"
    else:
        text = str(value) if value else "—"
    st.markdown(f"**{label}**")
    st.caption(text)


def sync_card_widgets(edited: dict[str, Any]) -> None:
    """위젯 키 값을 편집 버퍼와 동기화한다.

    - 위젯 키가 없으면 초기 값을 set
    - 새 SceneSchema를 적용한 직후 reset_card_widgets()로 호출되면 값을 덮어쓴다.

    위젯 렌더링 *전에* 호출해야 한다. 렌더링 후엔 StreamlitAPIException 발생.
    """
    for field_key, _, _ in ELEMENT_LABELS:
        widget_key = _widget_key(field_key)
        widget_value = _to_widget_value(field_key, edited.get(field_key))
        if widget_key not in st.session_state:
            st.session_state[widget_key] = widget_value


def reset_card_widgets() -> None:
    """새 분석 결과를 받았을 때 위젯 키를 새 값으로 덮어쓴다.

    set_current_scene() 직후, 다음 render_scene_cards() 호출 *전에* 부른다.
    """
    edited = get_edited_elements() or {}
    for field_key, _, _ in ELEMENT_LABELS:
        widget_key = _widget_key(field_key)
        st.session_state[widget_key] = _to_widget_value(field_key, edited.get(field_key))
