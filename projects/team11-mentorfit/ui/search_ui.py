from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402

from app.core.config import settings  # noqa: E402
from ui.api_client import (  # noqa: E402
    MentorFitApiError,
    create_combinations,
    create_mentor_candidates,
    create_report,
    create_team_profile_from_prompt,
    list_mentors,
)

st.set_page_config(page_title="Mentor-Fit", page_icon="🧭", layout="wide")


async def _build_team_report(prompt: str) -> None:
    st.session_state.candidates = []
    st.session_state.combinations = []
    st.session_state.recommendation_report = None
    st.session_state.recommendation_error = ""
    response = await create_team_profile_from_prompt(prompt, st.session_state.chat_messages)
    st.session_state.chat_messages = response.chat_messages
    st.session_state.team_profile = response.team_profile if response.ready_for_recommendation else None
    st.session_state.draft_profile = response.draft_profile
    st.session_state.team_report = response.team_report
    st.session_state.missing_fields = response.missing_fields
    st.session_state.next_question = response.next_question
    st.session_state.ready_for_recommendation = response.ready_for_recommendation
    st.session_state.collection_status = response.status


async def _run_recommendation_flow() -> None:
    team_profile = st.session_state.team_profile
    st.session_state.recommendation_error = ""
    st.session_state.candidates = []
    st.session_state.combinations = []
    st.session_state.mentors = []
    st.session_state.recommendation_report = None
    if team_profile is None:
        st.session_state.recommendation_error = "팀 정보 수집이 완료된 뒤 추천을 실행할 수 있습니다."
        return
    candidates = await create_mentor_candidates(
        team_profile,
        st.session_state.top_k,
        st.session_state.prefilter_top_n,
    )
    combinations = await create_combinations(team_profile, candidates)
    mentors = await list_mentors()
    report = await create_report(
        team_profile,
        st.session_state.team_report,
        candidates,
        combinations,
        mentors,
        st.session_state.current_matching_status,
    )
    st.session_state.candidates = candidates
    st.session_state.combinations = combinations
    st.session_state.mentors = mentors
    st.session_state.recommendation_report = report


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _init_state() -> None:
    defaults = {
        "chat_messages": [],
        "team_prompt_input_version": 0,
        "team_profile": None,
        "draft_profile": None,
        "team_report": "",
        "missing_fields": [],
        "next_question": None,
        "ready_for_recommendation": False,
        "collection_status": "collecting",
        "recommendation_error": "",
        "candidates": [],
        "combinations": [],
        "recommendation_report": None,
        "mentors": [],
        "current_matching_status": "",
        "top_k": settings.candidate_top_k,
        "prefilter_top_n": settings.prefilter_top_n,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_flow() -> None:
    for key in [
        "chat_messages",
        "team_prompt_input_version",
        "team_profile",
        "draft_profile",
        "team_report",
        "missing_fields",
        "next_question",
        "ready_for_recommendation",
        "collection_status",
        "recommendation_error",
        "candidates",
        "combinations",
        "recommendation_report",
        "mentors",
        "current_matching_status",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    _init_state()


def _render_chat_log() -> None:
    if not st.session_state.chat_messages:
        st.caption("아직 대화 기록이 없습니다.")
        return
    for message in st.session_state.chat_messages[-8:]:
        with st.chat_message(message.role):
            st.write(message.content)


def _render_team_profile() -> None:
    profile = st.session_state.team_profile or st.session_state.draft_profile
    if profile is None:
        st.info("좌측에 팀 정보를 입력하면 이 영역에 현재까지 정리된 팀 정보가 표시됩니다.")
        return

    st.subheader("팀 리포트")
    st.write(st.session_state.team_report)
    if st.session_state.missing_fields:
        st.warning("아직 추천 실행에 필요한 정보가 더 필요합니다.")
        st.caption("누락 항목: " + ", ".join(st.session_state.missing_fields))
    st.divider()
    st.subheader("현재까지 정리된 TeamProfile")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**기술 스택**  \n{profile.skills}")
        st.markdown(f"**팀원/R&R**  \n{profile.members_rnr}")
        st.markdown(f"**프로젝트/기술 목표**  \n{profile.project_plan_tech_goals}")
    with col_b:
        st.markdown(f"**과정 목표**  \n{profile.maestro_program_goals}")
        st.markdown(f"**멘토링 니즈**  \n{profile.mentoring_needs}")
        st.markdown(f"**선호 조건**  \n{profile.fit_conditions or '미입력'}")


_init_state()

with st.sidebar:
    st.header("설정")
    st.session_state.top_k = st.number_input("후보 멘토 수", 1, 20, st.session_state.top_k)
    st.session_state.prefilter_top_n = st.number_input("임베딩 사전 필터 수", 10, 100, st.session_state.prefilter_top_n)
    st.session_state.current_matching_status = st.text_area(
        "현재 매칭 현황 메모",
        value=st.session_state.current_matching_status,
        placeholder="예: 일부 멘토의 매칭 가능 여부는 운영진 확인 필요",
    )
    st.info(f"Mock Mode: {'ON' if settings.mock_mode else 'OFF'}")
    st.caption(f"API: {settings.api_base_url}")

st.title("Mentor-Fit 팀 리포트")
st.caption("팀 정보를 먼저 정리한 뒤, 실제 멘토 후보 검색과 조합 추천을 실행합니다.")

left, right = st.columns([3, 7], gap="large")

with left:
    st.subheader("팀 정보 입력")
    with st.container(height=440):
        _render_chat_log()
    prompt_key = f"team_prompt_input_{st.session_state.team_prompt_input_version}"
    prompt = st.text_area(
        "프롬프트",
        key=prompt_key,
        height=180,
        placeholder="팀원 역할, 기술 스택, 목표, 원하는 멘토링 등을 하나씩 입력하세요. 부족한 정보는 대화로 이어서 질문합니다.",
    )
    if st.button("팀 리포트 작성", type="primary", use_container_width=True):
        if not prompt.strip():
            st.warning("팀 정보를 먼저 입력해주세요.")
        else:
            try:
                with st.spinner("팀 리포트를 생성하는 중입니다..."):
                    _run_async(_build_team_report(prompt.strip()))
            except MentorFitApiError as exc:
                st.error(str(exc))
            else:
                st.session_state.team_prompt_input_version += 1
                st.rerun()
    if st.button("초기화", use_container_width=True):
        _reset_flow()
        st.rerun()

with right:
    _render_team_profile()
    if st.session_state.draft_profile is not None:
        st.divider()
        if not st.session_state.ready_for_recommendation:
            st.info("대화창의 추가 질문에 답하면 멘토 추천을 실행할 수 있습니다.")
        if st.button(
            "멘토 조합 추천받기!",
            type="primary",
            use_container_width=True,
            disabled=not st.session_state.ready_for_recommendation,
        ):
            st.session_state.recommendation_error = ""
            try:
                with st.spinner("후보 검색, 조합 생성, 최종 리포트 작성을 실행하는 중입니다..."):
                    _run_async(_run_recommendation_flow())
            except MentorFitApiError as exc:
                st.session_state.recommendation_error = str(exc)
            if st.session_state.recommendation_error:
                st.error(st.session_state.recommendation_error)
            else:
                try:
                    st.switch_page("pages/1_📊_추천_리포트.py")
                except Exception:
                    st.success("추천 리포트가 생성되었습니다. 좌측 페이지 메뉴에서 '추천 리포트'를 열어주세요.")

if st.session_state.candidates:
    with st.expander("최근 후보 추천 결과", expanded=False):
        mentors = {mentor.mentor_id: mentor for mentor in st.session_state.mentors}
        for candidate in st.session_state.candidates:
            mentor = mentors.get(candidate.mentor_id)
            st.markdown(f"**{candidate.rank}. {mentor.name if mentor else candidate.mentor_id}**")
            st.write(candidate.reason)
            st.caption(candidate.weak_point)
