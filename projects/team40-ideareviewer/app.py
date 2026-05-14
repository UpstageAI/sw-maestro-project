"""Streamlit entry point for the persona review demo."""

from __future__ import annotations

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
FOCUS_OPTIONS = ["사용성", "신뢰", "가격", "고령층 접근성", "재사용 의향", "운영 리스크"]


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


def _init_session_state() -> None:
    defaults = {
        "draft_description": "",
        "service_name": "",
        "stage": STAGES[0],
        "focus_areas": ["사용성", "신뢰"],
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

        focus_areas = st.multiselect(
            "중점 검토 항목",
            FOCUS_OPTIONS,
            key="focus_areas",
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

    raw_input = compose_review_input(
        service_name=service_name,
        stage=stage,
        focus_areas=focus_areas,
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

    with st.status("검토를 실행하고 있습니다.", expanded=True) as status:
        try:
            for event in stream_pipeline(raw_input):
                events.append(event)
                if event.update:
                    final_state.update(event.update)
                suffix = f" · {', '.join(event.update_keys)}" if event.update_keys else ""
                status.write(f"{event.label}{suffix}")
        except Exception as exc:
            st.session_state.last_error = str(exc)
            status.update(label="검토 실행 실패", state="error", expanded=True)
            st.error(str(exc))
            return

        status.update(label="검토 리포트가 준비되었습니다.", state="complete", expanded=False)

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

    brief = state.get("brief")
    persona_a = state.get("persona_a")
    persona_b = state.get("persona_b")

    st.divider()
    st.subheader("검토 리포트")
    metric_cols = st.columns(4)
    metric_cols[0].metric("서비스", _get(brief, "title", "입력 기획"))
    metric_cols[1].metric("참여 패널", "2명")
    metric_cols[2].metric("검토 단계", f"{len(events)}개")
    metric_cols[3].metric("최종 리포트", "완료" if state.get("final_review_text") else "대기")

    tabs = st.tabs(["요약 리포트", "사용자 패널", "1차 반응", "교차 리뷰", "근거 보기"])
    with tabs[0]:
        _render_summary_report(state)
    with tabs[1]:
        _render_persona_tab(persona_a, persona_b)
    with tabs[2]:
        _render_opinion_tab(state)
    with tabs[3]:
        _render_review_tab(state)
    with tabs[4]:
        _render_debug_tab(state, events)


def _render_summary_report(state: dict[str, Any]) -> None:
    brief = state.get("brief")
    final_review_text = state.get("final_review_text")

    st.markdown("#### 종합 리포트")
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


def _render_persona_tab(persona_a: Any, persona_b: Any) -> None:
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
        _render_opinion(state.get("persona_a"), state.get("opinion_a"))
    with col_b:
        _render_opinion(state.get("persona_b"), state.get("opinion_b"))


def _render_opinion(persona: Any, opinion: Any) -> None:
    with st.container(border=True):
        st.caption("1차 사용자 반응")
        st.subheader(_get(persona, "display_name", "-"))
        if opinion is None:
            st.warning("의견이 생성되지 않았습니다.")
            return

        would_use = "사용 의향 있음" if _get(opinion, "would_use", False) else "사용 의향 낮음"
        st.markdown(f'<span class="status-pill">{would_use}</span>', unsafe_allow_html=True)
        if _get(opinion, "would_use_description"):
            st.write(_get(opinion, "would_use_description"))

        st.markdown("**긍정 신호**")
        _render_reaction_points(_get(opinion, "positive_points", []))
        st.markdown("**우려 신호**")
        _render_reaction_points(_get(opinion, "negative_points", []))


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
        )
    with col_b:
        _render_review(
            reviewer=state.get("persona_b"),
            target=state.get("persona_a"),
            review=state.get("review_b"),
        )


def _render_review(reviewer: Any, target: Any, review: Any) -> None:
    with st.container(border=True):
        st.caption("교차 리뷰")
        st.subheader(f"{_get(reviewer, 'display_name', '-')} -> {_get(target, 'display_name', '-')}")
        if review is None:
            st.warning("교차 리뷰가 생성되지 않았습니다.")
            return

        for feedback in _as_list(_get(review, "point_feedbacks", [])):
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

    with st.expander("최종 state", expanded=False):
        st.json(_json_safe(state))


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
