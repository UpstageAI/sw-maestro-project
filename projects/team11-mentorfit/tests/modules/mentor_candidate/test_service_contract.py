import inspect

import pytest

from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile
from app.modules.mentor_candidate.service import get_mentor_candidates


@pytest.fixture
def team_profile() -> TeamProfile:
    return TeamProfile(
        members_rnr="리더(BE), 팀원(FE)",
        project_plan_tech_goals="LLM 서비스 구축",
        mentoring_needs="아키텍처 리뷰",
        fit_conditions="AI 경험 선호",
        maestro_program_goals="소마 인증",
        skills="Python, FastAPI",
    )


@pytest.fixture
def mentors() -> list[Mentor]:
    return [
        Mentor(
            mentor_id=1,
            name="멘토A",
            stacks=["Python"],
            hobbie="",
            target="기술",
            is_overseas=False,
            is_new_mentor=False,
            can_plan=True,
            meeting_mode_preference="온라인",
            domains=["AI"],
            is_certificated=False,
            career=[("회사A", 5)],
        )
    ]


def test_get_mentor_candidates_accepts_prefilter_top_n_parameter():
    signature = inspect.signature(get_mentor_candidates)

    assert "prefilter_top_n" in signature.parameters


@pytest.mark.asyncio
async def test_get_mentor_candidates_passes_prefilter_top_n(monkeypatch, team_profile: TeamProfile, mentors: list[Mentor]):
    captured: dict[str, int] = {}

    def fake_get_all_mentors() -> list[Mentor]:
        return mentors

    async def fake_filter_mentors(*, team_profile: TeamProfile, mentors: list[Mentor], top_n: int) -> list[Mentor]:
        captured["top_n"] = top_n
        return mentors

    async def fake_select_candidates(*, team_profile: TeamProfile, mentors: list[Mentor], top_k: int) -> list[CandidateResult]:
        return [
            CandidateResult(
                mentor_id=mentors[0].mentor_id,
                rank=1,
                reason="기술 스택이 적합합니다.",
                weak_point="일정 확인이 필요합니다.",
            )
        ]

    monkeypatch.setattr("app.modules.mentor_candidate.service.get_all_mentors", fake_get_all_mentors)
    monkeypatch.setattr("app.modules.mentor_candidate.service.filter_mentors", fake_filter_mentors)
    monkeypatch.setattr("app.modules.mentor_candidate.service.select_candidates", fake_select_candidates)

    result = await get_mentor_candidates(team_profile, top_k=1, prefilter_top_n=17)

    assert captured["top_n"] == 17
    assert result[0].mentor_id == 1


@pytest.mark.asyncio
async def test_get_mentor_candidates_defaults_to_settings_prefilter_top_n(
    monkeypatch,
    team_profile: TeamProfile,
    mentors: list[Mentor],
):
    captured: dict[str, int] = {}

    def fake_get_all_mentors() -> list[Mentor]:
        return mentors

    async def fake_filter_mentors(*, team_profile: TeamProfile, mentors: list[Mentor], top_n: int) -> list[Mentor]:
        captured["top_n"] = top_n
        return mentors

    async def fake_select_candidates(*, team_profile: TeamProfile, mentors: list[Mentor], top_k: int) -> list[CandidateResult]:
        return [
            CandidateResult(
                mentor_id=mentors[0].mentor_id,
                rank=1,
                reason="기술 스택이 적합합니다.",
                weak_point="일정 확인이 필요합니다.",
            )
        ]

    monkeypatch.setattr("app.modules.mentor_candidate.service.settings.prefilter_top_n", 23)
    monkeypatch.setattr("app.modules.mentor_candidate.service.get_all_mentors", fake_get_all_mentors)
    monkeypatch.setattr("app.modules.mentor_candidate.service.filter_mentors", fake_filter_mentors)
    monkeypatch.setattr("app.modules.mentor_candidate.service.select_candidates", fake_select_candidates)

    await get_mentor_candidates(team_profile, top_k=1)

    assert captured["top_n"] == 23
