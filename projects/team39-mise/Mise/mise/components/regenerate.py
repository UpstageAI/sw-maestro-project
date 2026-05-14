"""재생성 버튼 + 횟수 카운터.

콜백은 `st.button(on_click=...)` 패턴으로 등록하므로, 다음 rerun의 위젯 렌더링 *전에* 실행된다.
즉 콜백 안에서 set_current_scene → reset_card_widgets → append_history를 자유롭게 호출할 수 있다.
"""
from __future__ import annotations

from typing import Callable

import streamlit as st

from mise.state import (
    REGEN_LIMIT,
    Keys,
    can_regenerate,
    increment_regen,
    is_dirty,
)

RegenerateCallback = Callable[[], None]


def _on_click(callback: RegenerateCallback) -> None:
    if can_regenerate():
        increment_regen()
        callback()


def render_regenerate_button(
    on_regenerate: RegenerateCallback,
    label: str = "재생성",
    button_key: str = "d_regenerate_btn",
) -> None:
    """재생성 버튼을 그리고, 클릭 시 카운터 증가 + 콜백 실행.

    Args:
        on_regenerate: 새 SceneSchema/이미지 생성 + history append를 담당. 호출 시점은 다음 rerun 직전.
        label: 버튼 라벨.
        button_key: 위젯 키 (한 페이지에 여러 개 둘 일은 없지만 충돌 방지용).
    """
    used = st.session_state.get(Keys.REGEN_COUNT, 0)
    remaining = REGEN_LIMIT - used

    col_btn, col_count = st.columns([1, 2])
    with col_btn:
        st.button(
            label,
            disabled=not can_regenerate(),
            type="primary",
            width="stretch",
            key=button_key,
            on_click=_on_click,
            args=(on_regenerate,),
        )
    with col_count:
        if remaining > 0:
            if is_dirty():
                st.caption(f"남은 재생성: **{remaining}회** · 편집됨")
            else:
                st.caption(f"남은 재생성: **{remaining}회**")
        else:
            st.caption("재생성 한도(5회)를 모두 사용했습니다.")
