from __future__ import annotations

import sys
from html import escape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402

from app.modules.report.schemas import RecommendationReport, ReportCombination  # noqa: E402

st.set_page_config(page_title="추천 리포트", page_icon="📊", layout="wide")


def _chip(text: str, background: str = "#eef2ff", color: str = "#312e81") -> str:
    safe_text = escape(text)
    return (
        f'<span style="display:inline-block;padding:0.25rem 0.55rem;margin:0.12rem;'
        f'border-radius:999px;background:{background};color:{color};font-size:0.82rem;'
        f'font-weight:650;">{safe_text}</span>'
    )


def _render_chips(items: list[str], background: str = "#eef2ff", color: str = "#312e81") -> None:
    if items:
        st.markdown(" ".join(_chip(item, background, color) for item in items), unsafe_allow_html=True)
    else:
        st.caption("표시할 항목이 없습니다.")


def _render_combination(combination: ReportCombination) -> None:
    title = f"{combination.rank}. {combination.main_mentor.name} + "
    title += ", ".join(mentor.name for mentor in combination.supplement_mentors) or "보완 멘토 없음"
    with st.expander(title, expanded=combination.rank == 1):
        main_col, supplement_col = st.columns([1, 1])
        with main_col:
            st.markdown("#### 메인 멘토")
            st.markdown(f"**{combination.main_mentor.name}** (ID: {combination.main_mentor.mentor_id})")
            st.write(combination.main_mentor.reason)
            st.warning(combination.main_mentor.weak_point)
        with supplement_col:
            st.markdown("#### 보완 멘토")
            for mentor in combination.supplement_mentors:
                with st.container(border=True):
                    st.markdown(f"**{mentor.name}** (ID: {mentor.mentor_id})")
                    st.write(mentor.reason)
                    st.caption(mentor.weak_point)

        st.markdown("#### 조합 강점")
        _render_chips(combination.strengths, "#ecfdf5", "#047857")
        st.markdown("#### 조합 약점")
        _render_chips(combination.weak_points, "#fff7ed", "#c2410c")
        st.markdown("#### 추천 근거")
        st.write(combination.recommendation_reason)


def _go_home() -> None:
    try:
        st.switch_page("search_ui.py")
    except Exception:
        st.info("좌측 페이지 메뉴에서 메인 화면으로 돌아가세요.")


report: RecommendationReport | None = st.session_state.get("recommendation_report")
team_report = st.session_state.get("team_report", "")
candidates = st.session_state.get("candidates", [])

st.title("추천 리포트")

if report is None:
    st.warning("먼저 팀 리포트를 생성하고 멘토 조합 추천을 실행해주세요.")
    if st.button("팀 정보 입력으로 돌아가기", type="primary"):
        _go_home()
    st.stop()

st.caption(f"생성 시각: {report.generated_at}")

st.header("팀 요약")
st.write(report.team_summary)

if team_report:
    with st.expander("팀 리포트 원문", expanded=False):
        st.write(team_report)

st.divider()
st.header("후보 멘토 요약")
st.write(report.candidate_summary)
if candidates:
    for candidate in candidates:
        with st.container(border=True):
            st.markdown(f"**Rank {candidate.rank} · Mentor ID {candidate.mentor_id}**")
            st.success(candidate.reason)
            st.warning(candidate.weak_point)

st.divider()
st.header("추천 조합")
for combination in report.combinations:
    _render_combination(combination)

st.divider()
summary_col, confidence_col = st.columns([1, 1])
with summary_col:
    st.header("최종 추천")
    st.write(report.final_recommendation)
with confidence_col:
    st.header("신뢰도 판단 근거")
    st.write(report.confidence_basis)

st.header("주의사항")
for caution in report.cautions:
    st.markdown(f"- {caution}")

button_col_a, button_col_b = st.columns([1, 1])
with button_col_a:
    if st.button("다시 입력하기", use_container_width=True):
        _go_home()
with button_col_b:
    if st.button("리포트 초기화", use_container_width=True):
        for key in ["team_profile", "team_report", "candidates", "combinations", "recommendation_report"]:
            st.session_state.pop(key, None)
        _go_home()
