"""스타일 프리셋 라디오. 한국어 라벨 → 영문 키워드 매핑은 mise.state.STYLE_PRESETS."""
from __future__ import annotations

import streamlit as st

from mise.state import DEFAULT_STYLE_LABEL, Keys, STYLE_PRESETS


def render_style_preset(label: str = "이미지 스타일") -> str:
    """라디오를 그리고, 선택된 라벨의 영문 키워드를 반환한다."""
    options = list(STYLE_PRESETS.keys())
    current = st.session_state.get(Keys.STYLE_LABEL, DEFAULT_STYLE_LABEL)
    try:
        default_idx = options.index(current)
    except ValueError:
        default_idx = 0

    selected_label = st.radio(
        label,
        options=options,
        index=default_idx,
        horizontal=True,
        key=Keys.STYLE_LABEL,
    )
    return STYLE_PRESETS[selected_label]
