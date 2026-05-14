"""이미지 히스토리 컴포넌트. 최근 5개 썸네일을 보여주고, 클릭 시 확대 + 당시 프롬프트 표시.

session_state.HISTORY는 최신순(인덱스 0이 가장 최근).
"""
from __future__ import annotations

import io
from typing import Optional

import streamlit as st
from PIL import Image

from mise.state import (
    HistoryItem,
    get_history,
    get_selected_history,
    select_history,
)


def render_history_strip() -> None:
    """가로 스트립 형태로 최근 5개 썸네일을 그린다."""
    history = get_history()
    if not history:
        st.caption("아직 생성된 이미지가 없습니다.")
        return

    st.markdown("##### 최근 생성")
    cols = st.columns(len(history))
    for idx, (col, item) in enumerate(zip(cols, history)):
        with col:
            _render_thumbnail(idx, item)


def _render_thumbnail(idx: int, item: HistoryItem) -> None:
    if item.image_bytes:
        st.image(item.image_bytes, width="stretch")
    else:
        st.markdown("`이미지 없음`")
    caption = item.created_at.strftime("%H:%M:%S")
    badge = "최초" if item.mode == "generate" else f"재{idx}"
    st.caption(f"{badge} · {caption}")
    if st.button("자세히", key=f"d_hist_open_{idx}", width="stretch"):
        select_history(idx)


def render_history_detail() -> None:
    """선택된 히스토리 항목의 큰 이미지 + 당시 프롬프트/요소를 펼쳐서 보여준다."""
    selected = get_selected_history()
    if selected is None:
        return

    with st.container(border=True):
        header_col, close_col = st.columns([4, 1])
        with header_col:
            st.markdown(
                f"#### 히스토리 미리보기 — {selected.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        with close_col:
            if st.button("닫기", key="d_hist_close", width="stretch"):
                select_history(None)
                st.rerun()

        if selected.image_bytes:
            st.image(selected.image_bytes, width="stretch")
        st.caption(f"스타일: {selected.style_label} · 모드: {selected.mode}")

        with st.expander("당시 프롬프트", expanded=False):
            st.markdown("**Positive**")
            st.code(selected.prompt.get("positive_prompt", ""), language="text")
            st.markdown("**Negative**")
            st.code(selected.prompt.get("negative_prompt", ""), language="text")
            missing = selected.prompt.get("missing_info") or []
            if missing:
                st.markdown("**원문에서 부족한 정보**")
                for info in missing:
                    st.markdown(f"- {info}")

        with st.expander("당시 12요소", expanded=False):
            for key, value in selected.elements.items():
                if isinstance(value, list):
                    value = ", ".join(value) if value else "—"
                st.markdown(f"- **{key}**: {value or '—'}")

        with st.expander("원문", expanded=False):
            st.write(selected.novel_text)


def encode_image_to_bytes(image) -> Optional[bytes]:
    """PIL Image 또는 google.genai Image를 PNG bytes로 직렬화. None이면 None 반환."""
    if image is None:
        return None
    raw = getattr(image, "image_bytes", None)
    if raw is not None:
        return raw
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
