"""Streamlit entry point for the persona review demo."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from services.pipeline_runner import (
    PipelineEvent,
    compose_review_input,
    get_langsmith_status,
    get_persona_card_status,
    load_sample_raw_input,
    regenerate_persona_cards,
    stream_pipeline,
)

STAGES = ["아이디어", "프로토타입", "출시 전", "운영 중"]
RESULT_TAB_LABELS = ["요약 리포트", "사용자 패널", "1차 반응", "교차 리뷰", "실행 로그"]
_HIDDEN_RESULT_STATE_KEYS = {
    "persona_selection_reason",
    "opinion_quality_a",
    "opinion_quality_b",
    "review_quality_a",
    "review_quality_b",
}
_VISUAL_STAGES = [
    ("f0_parse", "기획 분석"),
    ("select_personas", "패널 선정"),
    ("generate_opinion", "1차 반응"),
    ("generate_review", "교차 리뷰"),
    ("supervisor_finalize", "보고서"),
]
_NEXT_VISUAL_NODE = {
    "f0_parse": "select_personas",
    "select_personas": "generate_opinion",
    "generate_opinion": "generate_review",
    "collect_opinions": "generate_review",
    "generate_review": "supervisor_finalize",
    "collect_reviews": "supervisor_finalize",
    "supervisor_finalize": None,
}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return list(value)


def _json_safe(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def _result_tab_labels() -> list[str]:
    return RESULT_TAB_LABELS.copy()


def _compose_raw_review_input(service_name: str, stage: str, description: str) -> str:
    return compose_review_input(
        service_name=service_name,
        stage=stage,
        focus_areas=[],
        description=description,
    )


def _quality_counts(quality: Any) -> tuple[int, int, int]:
    if quality is None:
        return (0, 0, 0)
    pass_ids = _as_list(_get(quality, "pass_point_ids", None)) or _as_list(_get(quality, "pass_feedback_ids", []))
    weak_ids = _as_list(_get(quality, "weak_point_ids", None)) or _as_list(_get(quality, "weak_feedback_ids", []))
    fail_ids = _as_list(_get(quality, "fail_point_ids", None)) or _as_list(_get(quality, "fail_feedback_ids", []))
    return (len(pass_ids), len(weak_ids), len(fail_ids))


def _allowed_point_ids(quality: Any, pass_key: str, weak_key: str) -> set[str] | None:
    if quality is None:
        return None
    return {
        *[str(item) for item in _as_list(_get(quality, pass_key, []))],
        *[str(item) for item in _as_list(_get(quality, weak_key, []))],
    }


def _filter_points_for_display(points: Any, quality: Any) -> list[Any]:
    items = _as_list(points)
    allowed = _allowed_point_ids(quality, "pass_point_ids", "weak_point_ids")
    if allowed is None:
        return items
    return [point for point in items if str(_get(point, "point_id", "")) in allowed]


def _filter_feedbacks_for_display(feedbacks: Any, quality: Any) -> list[Any]:
    items = _as_list(feedbacks)
    allowed = _allowed_point_ids(quality, "pass_feedback_ids", "weak_feedback_ids")
    if allowed is None:
        return items
    return [feedback for feedback in items if str(_get(feedback, "target_point_id", "")) in allowed]


def _decision_text(final_review_text: Any) -> str:
    text = str(final_review_text or "").strip()
    if text.startswith("[통과]"):
        return "통과"
    if text.startswith("[보류]"):
        return "보류"
    if text.startswith("[재검토]"):
        return "재검토"
    return "대기"


def _aggregate_quality_counts(state: dict[str, Any]) -> tuple[int, int, int]:
    pass_count = weak_count = fail_count = 0
    for key in ("opinion_quality_a", "opinion_quality_b", "review_quality_a", "review_quality_b"):
        passed, weak, failed = _quality_counts(state.get(key))
        pass_count += passed
        weak_count += weak
        fail_count += failed
    return pass_count, weak_count, fail_count


def _quality_flag_rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in ("opinion_quality_a", "opinion_quality_b", "review_quality_a", "review_quality_b"):
        report = state.get(key)
        for flag in _as_list(_get(report, "flags", [])):
            rows.append({
                "report": key,
                "severity": _get(flag, "severity", "-"),
                "code": _get(flag, "code", "-"),
                "point": _get(flag, "point_id", "-"),
                "message": _get(flag, "message", "-"),
            })
    return rows


def _public_result_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in state.items()
        if key not in _HIDDEN_RESULT_STATE_KEYS
    }


def _event_node_names(events: list[PipelineEvent]) -> set[str]:
    return {event.node_name for event in events}


def _visual_stage_class(node_name: str, events: list[PipelineEvent], running_node: str | None) -> str:
    if running_node == node_name:
        return "is-active"
    completed = _event_node_names(events)
    if node_name in completed:
        return "is-complete"
    if node_name == "generate_opinion" and "collect_opinions" in completed:
        return "is-complete"
    if node_name == "generate_review" and "collect_reviews" in completed:
        return "is-complete"
    return "is-pending"


def _persona_meta(persona: Any) -> str:
    meta = [
        _get(persona, "age_group"),
        _get(persona, "occupation"),
        _get(persona, "region"),
    ]
    return " / ".join(str(item) for item in meta if item) or "-"


def _selected_persona_card(label: str, persona: Any) -> str:
    name = escape(str(_get(persona, "display_name", "-")))
    meta = escape(_persona_meta(persona))
    summary = escape(str(_get(persona, "one_line_summary", "-")))
    return (
        '<div class="persona-card-selected">'
        f'<div class="persona-card-label">{escape(label)}</div>'
        f'<div class="persona-avatar">{name[:1]}</div>'
        f'<div class="persona-card-name">{name}</div>'
        f'<div class="persona-card-meta">{meta}</div>'
        f'<div class="persona-card-summary">{summary}</div>'
        "</div>"
    )


def _loading_persona_slot(label: str) -> str:
    return (
        '<div class="persona-slot is-loading">'
        f'<div class="persona-card-label">{escape(label)}</div>'
        '<div class="skeleton-avatar"></div>'
        '<div class="skeleton-line line-lg"></div>'
        '<div class="skeleton-line line-md"></div>'
        '<div class="skeleton-line line-sm"></div>'
        "</div>"
    )


def _scanning_candidate_cards() -> str:
    cards = []
    for index in range(7):
        cards.append(
            '<div class="scan-card">'
            '<div class="skeleton-avatar sm"></div>'
            '<div class="skeleton-line line-md"></div>'
            '<div class="skeleton-line line-sm"></div>'
            f'<span class="scan-label">익명 후보 {index + 1}</span>'
            "</div>"
        )
    return (
        '<div class="persona-scan-window">'
        '<div class="persona-scan-track">'
        + "".join(cards)
        + "".join(cards)
        + "</div></div>"
    )


def _stage_chips_html(events: list[PipelineEvent], running_node: str | None) -> str:
    chips = []
    for node_name, label in _VISUAL_STAGES:
        stage_class = _visual_stage_class(node_name, events, running_node)
        chips.append(f'<span class="stage-chip {stage_class}">{escape(label)}</span>')
    return '<div class="stage-chip-row">' + "".join(chips) + "</div>"


def _build_persona_visual_html(
    state: dict[str, Any],
    events: list[PipelineEvent],
    running_node: str | None = None,
) -> str:
    persona_a = state.get("persona_a")
    persona_b = state.get("persona_b")
    has_selection = persona_a is not None and persona_b is not None
    title = "선택된 가상 사용자 패널" if has_selection else "가상 사용자 패널 선정 중"
    subtitle = (
        "기획안과 맞는 2명의 패널이 확정되었습니다."
        if has_selection
        else "익명 후보 카드를 훑으며 이번 검토에 맞는 패널 2명을 고르고 있습니다."
    )

    if has_selection:
        body = (
            '<div class="persona-selection-grid">'
            + _selected_persona_card("패널 A · 선정 완료", persona_a)
            + _selected_persona_card("패널 B · 선정 완료", persona_b)
            + "</div>"
        )
    else:
        body = (
            _scanning_candidate_cards()
            + '<div class="persona-selection-grid">'
            + _loading_persona_slot("패널 A")
            + _loading_persona_slot("패널 B")
            + "</div>"
        )

    return (
        '<section class="persona-visualizer">'
        f'<div class="visualizer-kicker">{escape(title)}</div>'
        f'<div class="visualizer-copy">{escape(subtitle)}</div>'
        f"{body}"
        f"{_stage_chips_html(events, running_node)}"
        "</section>"
    )


def _init_session_state() -> None:
    defaults = {
        "draft_description": "",
        "service_name": "",
        "stage": STAGES[0],
        "review_state": None,
        "review_events": [],
        "last_error": None,
        "run_history": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        .app-eyebrow {
            color: #4f6f66;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
        }
        .app-subtitle {
            color: #5f656d;
            font-size: 0.98rem;
            margin-top: -0.5rem;
            margin-bottom: 1.25rem;
        }
        .section-note {
            color: #69707a;
            font-size: 0.9rem;
        }
        .status-pill {
            border: 1px solid #d8e1dd;
            border-radius: 6px;
            color: #34443f;
            display: inline-block;
            font-size: 0.82rem;
            margin: 0 0.35rem 0.35rem 0;
            padding: 0.2rem 0.55rem;
        }
        .persona-visualizer {
            background: #fbfcfc;
            border: 1px solid #dde6e2;
            border-radius: 8px;
            margin: 1rem 0 1.25rem;
            overflow: hidden;
            padding: 1rem;
        }
        .visualizer-kicker {
            color: #263b35;
            font-size: 0.98rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .visualizer-copy {
            color: #66726f;
            font-size: 0.88rem;
            margin-bottom: 0.85rem;
        }
        .persona-scan-window {
            background: #f4f7f6;
            border: 1px solid #e2e9e6;
            border-radius: 8px;
            margin-bottom: 0.9rem;
            overflow: hidden;
            padding: 0.75rem 0;
        }
        .persona-scan-track {
            animation: persona-scan 16s linear infinite;
            display: flex;
            gap: 0.7rem;
            width: max-content;
        }
        .scan-card,
        .persona-slot,
        .persona-card-selected {
            background: #ffffff;
            border: 1px solid #dfe7e4;
            border-radius: 8px;
            min-height: 136px;
            padding: 0.85rem;
        }
        .scan-card {
            flex: 0 0 148px;
            opacity: 0.72;
            position: relative;
        }
        .scan-label {
            color: transparent;
            font-size: 0.01rem;
            user-select: none;
        }
        .persona-selection-grid {
            display: grid;
            gap: 0.9rem;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .persona-slot.is-loading {
            animation: persona-pulse 1.8s ease-in-out infinite;
        }
        .persona-card-selected {
            border-color: #a9c7bd;
            box-shadow: inset 0 0 0 1px #d8e8e2;
        }
        .persona-card-label {
            color: #4f6f66;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }
        .persona-avatar,
        .skeleton-avatar {
            align-items: center;
            background: #e8efec;
            border-radius: 999px;
            color: #315149;
            display: flex;
            font-weight: 700;
            height: 2.4rem;
            justify-content: center;
            margin-bottom: 0.65rem;
            width: 2.4rem;
        }
        .skeleton-avatar.sm {
            height: 1.8rem;
            width: 1.8rem;
        }
        .skeleton-line {
            animation: shimmer 1.8s ease-in-out infinite;
            background: linear-gradient(90deg, #e8eeeb 0%, #f6f8f7 45%, #e1e8e5 100%);
            background-size: 180% 100%;
            border-radius: 999px;
            height: 0.65rem;
            margin: 0.45rem 0;
        }
        .line-lg { width: 78%; }
        .line-md { width: 58%; }
        .line-sm { width: 38%; }
        .persona-card-name {
            color: #1f2e2a;
            font-size: 1.03rem;
            font-weight: 700;
        }
        .persona-card-meta {
            color: #64716d;
            font-size: 0.84rem;
            margin-top: 0.2rem;
        }
        .persona-card-summary {
            color: #34443f;
            font-size: 0.9rem;
            margin-top: 0.65rem;
        }
        .stage-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.9rem;
        }
        .stage-chip {
            border: 1px solid #d6dfdb;
            border-radius: 999px;
            color: #66726f;
            font-size: 0.78rem;
            padding: 0.18rem 0.55rem;
        }
        .stage-chip.is-active {
            background: #e9f4ef;
            border-color: #9cc5b7;
            color: #24483f;
            font-weight: 700;
        }
        .stage-chip.is-complete {
            background: #f2f7f5;
            color: #315149;
        }
        @keyframes persona-scan {
            from { transform: translateX(0); }
            to { transform: translateX(-50%); }
        }
        @keyframes persona-pulse {
            0%, 100% { opacity: 0.72; }
            50% { opacity: 1; }
        }
        @keyframes shimmer {
            0% { background-position: 120% 0; }
            100% { background-position: -80% 0; }
        }
        @media (max-width: 760px) {
            .persona-selection-grid {
                grid-template-columns: 1fr;
            }
        }
        div[data-testid="stMetric"] {
            background: #f7f9f8;
            border: 1px solid #e2e8e5;
            border-radius: 8px;
            padding: 0.7rem 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _reset_review() -> None:
    st.session_state.review_state = None
    st.session_state.review_events = []
    st.session_state.last_error = None


def _render_sidebar() -> None:
    card_status = get_persona_card_status()
    langsmith = get_langsmith_status()

    with st.sidebar:
        st.header("워크스페이스")
        if st.button("새 검토", use_container_width=True):
            _reset_review()
            st.rerun()

        if st.button("샘플 입력 불러오기", use_container_width=True):
            st.session_state.draft_description = load_sample_raw_input()
            st.rerun()

        st.divider()
        st.subheader("페르소나 데이터")
        if card_status.exists:
            st.success(f"{card_status.count}개 카드 준비됨")
        else:
            st.error("persona card가 없습니다")
        st.caption(str(card_status.path))

        if st.button("페르소나 카드 재생성", use_container_width=True):
            with st.spinner("페르소나 카드를 생성하는 중입니다."):
                regenerate_persona_cards()
            st.success("재생성 완료")
            st.rerun()

        st.divider()
        st.subheader("최근 검토")
        history = st.session_state.run_history
        if not history:
            st.caption("아직 실행된 검토가 없습니다.")
        for item in history[:5]:
            st.caption(f"{item['title']} · {item['event_count']}단계")

        with st.expander("개발자 정보", expanded=False):
            st.write("LangSmith tracing:", "ON" if langsmith.tracing_enabled else "OFF")
            st.write("Project:", langsmith.project)
            st.write("Endpoint:", langsmith.endpoint)
            st.write("API key:", "configured" if langsmith.has_api_key else "missing")


def _render_header() -> None:
    st.markdown('<div class="app-eyebrow">Persona Review Studio</div>', unsafe_allow_html=True)
    st.title("페르소나 기반 기획 검토")
    st.markdown(
        '<div class="app-subtitle">기획을 자유롭게 입력하면 가상 사용자 패널이 1차 반응, 교차 리뷰, 최종 검토 리포트를 생성합니다.</div>',
        unsafe_allow_html=True,
    )


def _render_pipeline_visualizer(
    state: dict[str, Any],
    events: list[PipelineEvent],
    running_node: str | None = None,
) -> None:
    st.markdown(
        _build_persona_visual_html(state=state, events=events, running_node=running_node),
        unsafe_allow_html=True,
    )


def _render_input_form() -> None:
    with st.form("review_request_form", border=True):
        st.subheader("검토 요청서")
        col_name, col_stage = st.columns([2, 1])
        with col_name:
            service_name = st.text_input(
                "서비스 이름",
                key="service_name",
                placeholder="예: 시니어 케어 예약 도우미",
            )
        with col_stage:
            stage = st.radio(
                "현재 단계",
                STAGES,
                horizontal=True,
                key="stage",
            )

        description = st.text_area(
            "기획을 자유롭게 입력하세요",
            key="draft_description",
            height=220,
            placeholder=(
                "어떤 사용자를 위한 서비스인지, 핵심 기능은 무엇인지, "
                "특히 걱정되는 지점은 무엇인지 자연스럽게 적어주세요."
            ),
        )

        submitted = st.form_submit_button("페르소나 리뷰 시작", type="primary")

    if not submitted:
        return

    raw_input = _compose_raw_review_input(
        service_name=service_name,
        stage=stage,
        description=description,
    )
    if not description.strip():
        st.warning("검토할 기획 설명을 입력해 주세요.")
        return

    if not get_persona_card_status().exists:
        st.error("페르소나 카드가 없어 실행할 수 없습니다. 사이드바에서 카드를 재생성해 주세요.")
        return

    _run_review(raw_input=raw_input, display_title=service_name or "이름 없는 검토")


def _run_review(raw_input: str, display_title: str) -> None:
    events: list[PipelineEvent] = []
    final_state: dict[str, Any] = {}
    st.session_state.last_error = None
    visual_slot = st.empty()
    visual_slot.markdown(
        _build_persona_visual_html(final_state, events, running_node="f0_parse"),
        unsafe_allow_html=True,
    )

    with st.status("검토를 실행하고 있습니다.", expanded=True) as status:
        try:
            for event in stream_pipeline(raw_input):
                events.append(event)
                if event.update:
                    final_state.update(event.update)
                running_node = _NEXT_VISUAL_NODE.get(event.node_name)
                visual_slot.markdown(
                    _build_persona_visual_html(final_state, events, running_node=running_node),
                    unsafe_allow_html=True,
                )
                suffix = f" · {', '.join(event.update_keys)}" if event.update_keys else ""
                status.write(f"{event.label}{suffix}")
        except Exception as exc:
            st.session_state.last_error = str(exc)
            status.update(label="검토 실행 실패", state="error", expanded=True)
            st.error(str(exc))
            return

        status.update(label="검토 리포트가 준비되었습니다.", state="complete", expanded=False)

    visual_slot.empty()
    st.session_state.review_state = final_state
    st.session_state.review_events = events
    st.session_state.run_history.insert(
        0,
        {
            "title": display_title,
            "event_count": len(events),
        },
    )


def _render_empty_state() -> None:
    st.info("검토 요청서를 작성하고 실행하면 이 영역에 리포트가 생성됩니다.")


def _render_results() -> None:
    state = st.session_state.review_state
    events = st.session_state.review_events
    if not state:
        _render_empty_state()
        return

    persona_a = state.get("persona_a")
    persona_b = state.get("persona_b")

    st.divider()
    st.subheader("검토 리포트")
    passed, weak, failed = _aggregate_quality_counts(state)
    metric_cols = st.columns(4)
    metric_cols[0].metric("최종 판단", _decision_text(state.get("final_review_text")))
    metric_cols[1].metric("검증 산출물", f"{passed + weak}개", delta=f"보류 {weak}개")
    metric_cols[2].metric("제외 산출물", f"{failed}개")
    metric_cols[3].metric("실행 단계", f"{len(events)}개")
    _render_pipeline_visualizer(state, events)

    tabs = st.tabs(_result_tab_labels())
    with tabs[0]:
        _render_summary_report(state)
    with tabs[1]:
        _render_persona_tab(persona_a, persona_b, state)
    with tabs[2]:
        _render_opinion_tab(state)
    with tabs[3]:
        _render_review_tab(state)
    with tabs[4]:
        _render_debug_tab(state, events)


def _render_summary_report(state: dict[str, Any]) -> None:
    brief = state.get("brief")
    final_review_text = state.get("final_review_text")
    passed, weak, failed = _aggregate_quality_counts(state)

    st.markdown("#### 종합 리포트")
    st.caption(
        f"품질 게이트 기준으로 통과 {passed}개, 보류 {weak}개, 제외 {failed}개 산출물을 반영했습니다."
    )
    if final_review_text:
        st.markdown(final_review_text)
    else:
        st.warning("최종 리포트가 아직 생성되지 않았습니다.")

    with st.expander("분석된 기획안", expanded=False):
        st.write("제목:", _get(brief, "title", "-"))
        st.write("대상:", _get(brief, "target", "-"))
        st.write("설명:", _get(brief, "description", "-"))
        features = _as_list(_get(brief, "key_features", []))
        if features:
            st.write("핵심 기능")
            for feature in features:
                st.markdown(f"- {feature}")
        if _get(brief, "concerns"):
            st.write("우려:", _get(brief, "concerns"))


def _render_persona_tab(persona_a: Any, persona_b: Any, state: Any = None) -> None:
    st.markdown("#### 이번 검토에 참여한 가상 사용자 패널")
    col_a, col_b = st.columns(2)
    with col_a:
        _render_persona_card("패널 A", persona_a)
    with col_b:
        _render_persona_card("패널 B", persona_b)


def _render_persona_card(label: str, persona: Any) -> None:
    with st.container(border=True):
        st.caption(label)
        st.subheader(_get(persona, "display_name", "-"))
        meta = [
            _get(persona, "age_group"),
            _get(persona, "sex"),
            _get(persona, "occupation"),
            _get(persona, "region"),
        ]
        st.caption(" / ".join([str(item) for item in meta if item]))
        st.write(_get(persona, "one_line_summary", "-"))

        st.markdown("**생활 맥락**")
        st.write(_get(persona, "life_context", "-"))

        col_goal, col_pain = st.columns(2)
        with col_goal:
            st.markdown("**목표**")
            for item in _as_list(_get(persona, "user_goals", [])):
                st.markdown(f"- {item}")
        with col_pain:
            st.markdown("**불편**")
            for item in _as_list(_get(persona, "pain_points", [])):
                st.markdown(f"- {item}")

        st.markdown("**말투**")
        st.write(_get(persona, "speaking_style", "-"))


def _render_opinion_tab(state: dict[str, Any]) -> None:
    col_a, col_b = st.columns(2)
    with col_a:
        _render_opinion(
            state.get("persona_a"),
            state.get("opinion_a"),
            state.get("opinion_quality_a"),
        )
    with col_b:
        _render_opinion(
            state.get("persona_b"),
            state.get("opinion_b"),
            state.get("opinion_quality_b"),
        )


def _render_opinion(persona: Any, opinion: Any, quality: Any = None) -> None:
    with st.container(border=True):
        st.caption("1차 사용자 반응")
        st.subheader(_get(persona, "display_name", "-"))
        if opinion is None:
            st.warning("의견이 생성되지 않았습니다.")
            return

        passed, weak, failed = _quality_counts(quality)
        st.caption(f"표시 기준: 통과 {passed}개 · 보류 {weak}개 · 제외 {failed}개")
        would_use = "사용 의향 있음" if _get(opinion, "would_use", False) else "사용 의향 낮음"
        st.markdown(f'<span class="status-pill">{would_use}</span>', unsafe_allow_html=True)
        if _get(opinion, "would_use_description"):
            st.write(_get(opinion, "would_use_description"))

        st.markdown("**긍정 신호**")
        _render_reaction_points(_filter_points_for_display(_get(opinion, "positive_points", []), quality))
        st.markdown("**우려 신호**")
        _render_reaction_points(_filter_points_for_display(_get(opinion, "negative_points", []), quality))


def _render_reaction_points(points: Any) -> None:
    items = _as_list(points)
    if not items:
        st.caption("표시할 항목이 없습니다.")
        return
    for point in items:
        st.markdown(f"- **{_get(point, 'title', '-')}**")
        st.write(_get(point, "detail", "-"))


def _render_review_tab(state: dict[str, Any]) -> None:
    col_a, col_b = st.columns(2)
    with col_a:
        _render_review(
            reviewer=state.get("persona_a"),
            target=state.get("persona_b"),
            review=state.get("review_a"),
            quality=state.get("review_quality_a"),
        )
    with col_b:
        _render_review(
            reviewer=state.get("persona_b"),
            target=state.get("persona_a"),
            review=state.get("review_b"),
            quality=state.get("review_quality_b"),
        )


def _render_review(reviewer: Any, target: Any, review: Any, quality: Any = None) -> None:
    with st.container(border=True):
        st.caption("교차 리뷰")
        st.subheader(f"{_get(reviewer, 'display_name', '-')} -> {_get(target, 'display_name', '-')}")
        if review is None:
            st.warning("교차 리뷰가 생성되지 않았습니다.")
            return

        passed, weak, failed = _quality_counts(quality)
        st.caption(f"표시 기준: 통과 {passed}개 · 보류 {weak}개 · 제외 {failed}개")
        for feedback in _filter_feedbacks_for_display(_get(review, "point_feedbacks", []), quality):
            agreement = "동의" if _get(feedback, "agreement") == "agree" else "이견"
            st.markdown(
                f"**{agreement} · {_get(feedback, 'target_point_id', '-')}**"
            )
            st.write(_get(feedback, "comment", "-"))

        st.markdown("**종합 의견**")
        st.write(_get(review, "overall_comment", "-"))
        revised = "최종 사용 의향 있음" if _get(review, "revised_would_use", False) else "최종 사용 의향 낮음"
        st.markdown(f'<span class="status-pill">{revised}</span>', unsafe_allow_html=True)


def _render_debug_tab(state: dict[str, Any], events: list[PipelineEvent]) -> None:
    st.markdown("#### 실행 단계")
    st.dataframe(
        [
            {
                "step": index + 1,
                "node": event.node_name,
                "label": event.label,
                "updated": ", ".join(event.update_keys),
            }
            for index, event in enumerate(events)
        ],
        use_container_width=True,
        hide_index=True,
    )

    flag_rows = _quality_flag_rows(state)
    st.markdown("#### 품질 진단")
    if flag_rows:
        st.dataframe(flag_rows, use_container_width=True, hide_index=True)
    else:
        st.caption("품질 플래그가 없습니다.")

    with st.expander("최종 state", expanded=False):
        st.json(_json_safe(_public_result_state(state)))


def main() -> None:
    st.set_page_config(
        page_title="Persona Review Studio",
        page_icon="PRS",
        layout="wide",
    )
    _init_session_state()
    _inject_styles()
    _render_sidebar()
    _render_header()
    _render_input_form()

    if st.session_state.last_error:
        st.error(st.session_state.last_error)
    _render_results()


if __name__ == "__main__":
    main()
