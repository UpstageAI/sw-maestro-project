from __future__ import annotations

import html
from datetime import datetime
from typing import Any

import streamlit as st

from mise.components.history import encode_image_to_bytes
from mise.generators.image_generator import generate_image
from mise.models.scene_schema import SceneSchema


MAX_RESULTS = 5
MAX_INPUT_LENGTH = 1000

STYLE_PRESETS = {
    "시네마틱": "cinematic",
    "수채화": "watercolor painting",
    "픽셀아트": "pixel art",
    "웹툰풍": "webtoon style",
}

ELEMENT_LABELS = {
    "character": "인물",
    "background": "배경",
    "time": "시간",
    "place": "장소",
    "objects": "사물",
    "action": "행동",
    "emotion": "감정",
    "mood": "분위기",
    "color": "색감",
    "lighting": "조명",
    "camera_view": "시점",
    "composition": "구도",
}

SOURCE_LABELS = {
    "original": ("원문", "#2563eb", "#eff6ff"),
    "inferred": ("추론", "#c2410c", "#fff7ed"),
    "missing": ("부족", "#6b7280", "#f9fafb"),
}


def init_session_state() -> None:
    if "results" not in st.session_state:
        st.session_state.results = []
    if "current_result" not in st.session_state:
        st.session_state.current_result = None
    if "current_input" not in st.session_state:
        st.session_state.current_input = ""
    if "selected_style_label" not in st.session_state:
        st.session_state.selected_style_label = "시네마틱"


def add_result(
    result: SceneSchema,
    novel_text: str,
    style_label: str,
    image_bytes: bytes | None = None,
) -> None:
    item = {
        "created_at": datetime.now().strftime("%H:%M:%S"),
        "novel_text": novel_text,
        "style_label": style_label,
        "scene": result.model_dump(),
        "image_bytes": image_bytes,
    }
    st.session_state.results.append(item)
    st.session_state.results = st.session_state.results[-MAX_RESULTS:]
    st.session_state.current_result = item


def run_generate_image(scene: SceneSchema, style_value: str):
    return generate_image(
        positive=scene.prompt.positive_prompt,
        negative=scene.prompt.negative_prompt,
        style=style_value,
    )


def run_extract_scene(
    novel_text: str,
    style_value: str,
    mode: str = "generate",
    prev_scene: dict[str, Any] | None = None,
    changed_values: dict[str, Any] | None = None,
) -> SceneSchema:
    from mise.chains.scene_extractor import extract_scene

    return extract_scene(
        novel_text,
        mode=mode,
        prev_scene=prev_scene,
        changed_values=changed_values,
    )


def render_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1120px;
            padding-top: 2rem;
        }
        .mise-card {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 14px 14px 12px;
            min-height: 148px;
            background: #ffffff;
        }
        .mise-card-title {
            font-size: 0.92rem;
            font-weight: 700;
            margin-bottom: 8px;
            color: #111827;
        }
        .mise-card-body {
            font-size: 0.92rem;
            line-height: 1.5;
            color: #374151;
            overflow-wrap: anywhere;
        }
        .mise-badge {
            display: inline-block;
            margin-top: 10px;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 700;
        }
        .mise-empty {
            border: 1px dashed #d1d5db;
            border-radius: 8px;
            padding: 26px;
            color: #6b7280;
            background: #f9fafb;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_source_badge(source: str) -> str:
    label, color, background = SOURCE_LABELS.get(source, SOURCE_LABELS["missing"])
    return (
        f"<span class='mise-badge' style='color:{color};"
        f"background:{background};'>{label}</span>"
    )


def format_element_value(key: str, value: Any) -> str:
    if key == "objects" and isinstance(value, list):
        return ", ".join(value) if value else "정보 없음"
    return str(value).strip() if value else "정보 없음"


def render_element_cards(scene: dict[str, Any]) -> None:
    elements = scene["elements"]
    source_type = scene.get("source_type", {})

    for row_start in range(0, len(ELEMENT_LABELS), 4):
        cols = st.columns(4)
        for col, key in zip(cols, list(ELEMENT_LABELS)[row_start : row_start + 4]):
            value = html.escape(format_element_value(key, elements.get(key)))
            source = source_type.get(key, "missing")
            with col:
                st.markdown(
                    f"""
                    <div class="mise-card">
                        <div class="mise-card-title">{ELEMENT_LABELS[key]}</div>
                        <div class="mise-card-body">{value}</div>
                        {render_source_badge(source)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_prompt_preview(scene: dict[str, Any]) -> None:
    prompt = scene["prompt"]
    with st.expander("프롬프트 미리보기", expanded=True):
        st.caption("Positive Prompt")
        st.code(prompt.get("positive_prompt", ""), language="text")
        st.caption("Negative Prompt")
        st.code(prompt.get("negative_prompt", ""), language="text")

        missing_info = prompt.get("missing_info", [])
        if missing_info:
            st.caption("부족한 정보")
            st.write(", ".join(missing_info))


def render_generated_image(item: dict[str, Any]) -> None:
    st.subheader("생성된 이미지")
    image_bytes = item.get("image_bytes")
    if image_bytes:
        st.image(image_bytes, width="stretch")
        return
    st.markdown(
        """
        <div class="mise-empty">
            이번 결과에는 이미지가 없습니다. 시각화/재생성을 다시 시도해주세요.
        </div>
        """,
        unsafe_allow_html=True,
    )


def parse_objects(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def render_regenerate_form(current: dict[str, Any], novel_text: str, style_value: str) -> None:
    with st.form("regenerate_form"):
        st.subheader("장면 요소 보정")
        st.caption("값을 수정한 뒤 프롬프트만 다시 생성할 수 있습니다.")

        edited_elements: dict[str, Any] = {}
        elements = current["scene"]["elements"]

        for row_start in range(0, len(ELEMENT_LABELS), 2):
            cols = st.columns(2)
            for col, key in zip(cols, list(ELEMENT_LABELS)[row_start : row_start + 2]):
                label = ELEMENT_LABELS[key]
                value = elements.get(key, [])
                with col:
                    if key == "objects":
                        edited_elements[key] = parse_objects(
                            st.text_input(label, value=", ".join(value), key=f"edit_{key}")
                        )
                    else:
                        edited_elements[key] = st.text_input(label, value=value, key=f"edit_{key}")

        submitted = st.form_submit_button("수정 내용으로 프롬프트 재생성")

    if submitted:
        prev_scene = {
            "elements": edited_elements,
            "source_type": current["scene"].get("source_type", {}),
            "prompt": {"style": style_value},
        }
        changed_values = {
            key: edited_elements[key]
            for key in edited_elements
            if edited_elements[key] != elements.get(key)
        }
        try:
            with st.spinner("수정된 장면 요소로 프롬프트를 다시 생성하는 중입니다..."):
                result = run_extract_scene(
                    novel_text,
                    style_value,
                    mode="regenerate",
                    prev_scene=prev_scene,
                    changed_values=changed_values,
                )
            result = SceneSchema(
                elements=result.elements,
                source_type=result.source_type,
                prompt=result.prompt.model_copy(update={"style": style_value}),
            )
            with st.spinner("이미지를 다시 생성하는 중입니다... (10–20초)"):
                image = run_generate_image(result, style_value)
            add_result(
                result,
                novel_text,
                st.session_state.selected_style_label,
                image_bytes=encode_image_to_bytes(image),
            )
            st.success("이미지를 다시 생성했습니다.")
            st.rerun()
        except Exception as exc:
            st.error(f"재생성 중 문제가 발생했습니다: {exc}")


def render_history() -> None:
    if not st.session_state.results:
        return

    st.subheader("이전 결과")
    tabs = st.tabs(
        [
            f"{idx + 1}. {item['style_label']} · {item['created_at']}"
            for idx, item in enumerate(reversed(st.session_state.results))
        ]
    )
    for tab, item in zip(tabs, reversed(st.session_state.results)):
        with tab:
            preview = item["novel_text"][:120]
            st.caption(preview + ("..." if len(item["novel_text"]) > 120 else ""))
            if st.button("이 결과 보기", key=f"history_{item['created_at']}"):
                st.session_state.current_result = item
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="Mise", page_icon="M", layout="wide")
    init_session_state()
    render_styles()

    st.title("Mise")
    st.caption("소설 속 장면을 분석해 이미지 생성용 프롬프트로 변환합니다.")

    input_col, option_col = st.columns([3, 1])
    with input_col:
        novel_text = st.text_area(
            "소설 텍스트",
            value=st.session_state.current_input,
            height=220,
            max_chars=MAX_INPUT_LENGTH,
            placeholder="시각화하고 싶은 소설 속 장면 묘사를 붙여넣으세요.",
        )
    with option_col:
        char_count = len(novel_text or "")
        st.metric("글자 수", f"{char_count} / {MAX_INPUT_LENGTH}")
        style_label = st.selectbox(
            "스타일",
            options=list(STYLE_PRESETS),
            index=list(STYLE_PRESETS).index(st.session_state.selected_style_label),
        )
        st.session_state.selected_style_label = style_label
        style_value = STYLE_PRESETS[style_label]
        visualize = st.button("시각화", type="primary", use_container_width=True)

    if visualize:
        if not novel_text or not novel_text.strip():
            st.warning("소설 텍스트를 입력해주세요.")
        else:
            try:
                with st.spinner("장면 분석과 프롬프트 생성을 진행하는 중입니다..."):
                    result = run_extract_scene(novel_text, style_value)
                result = SceneSchema(
                    elements=result.elements,
                    source_type=result.source_type,
                    prompt=result.prompt.model_copy(update={"style": style_value}),
                )
                with st.spinner("이미지를 생성하는 중입니다... (10–20초)"):
                    image = run_generate_image(result, style_value)
                st.session_state.current_input = novel_text
                add_result(
                    result,
                    novel_text,
                    style_label,
                    image_bytes=encode_image_to_bytes(image),
                )
                st.success("이미지 생성이 완료되었습니다.")
            except Exception as exc:
                st.error(f"이미지 생성 중 문제가 발생했습니다: {exc}")

    current = st.session_state.current_result
    if current:
        st.divider()
        st.subheader("장면 분석 결과")
        render_element_cards(current["scene"])
        render_prompt_preview(current["scene"])
        render_generated_image(current)
        render_regenerate_form(current, current["novel_text"], STYLE_PRESETS[current["style_label"]])
        render_history()
    else:
        st.info("소설 문단을 입력하고 시각화를 시작하면 분석 결과가 여기에 표시됩니다.")


if __name__ == "__main__":
    main()
