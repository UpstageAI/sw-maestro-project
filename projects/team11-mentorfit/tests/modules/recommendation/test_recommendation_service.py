from __future__ import annotations

import pytest

from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile
from app.modules.recommendation.schemas import RecommendationRequest
from app.modules.recommendation.service import (
    RecommendationNotReadyError,
    UnknownCandidateMentorError,
    create_recommendation,
)
from app.modules.report.schemas import RecommendationReport
from app.modules.team_profile.schemas import ChatMessage


@pytest.fixture
def team_profile() -> TeamProfile:
    return TeamProfile(
        members_rnr="리더는 백엔드, 팀원은 프론트엔드를 담당합니다.",
        project_plan_tech_goals="LLM 기반 멘토 추천 서비스를 구축합니다.",
        mentoring_needs="아키텍처 리뷰와 추천 품질 개선 피드백이 필요합니다.",
        fit_conditions="AI 서비스 운영 경험이 있는 멘토를 선호합니다.",
        maestro_program_goals="인증",
        skills="Python, FastAPI",
    )


@pytest.fixture
def mentor() -> Mentor:
    return Mentor(
        mentor_id=1,
        name="테스트멘토",
        stacks=["Python"],
        hobbie="",
        target="기술 성장",
        is_overseas=False,
        is_new_mentor=False,
        can_plan=True,
        meeting_mode_preference="온라인",
        domains=["AI"],
        is_certificated=True,
        career=[("테스트회사", 5)],
    )


def recommendation_request(
    team_profile: TeamProfile | None,
    draft_profile: TeamProfile | None = None,
) -> RecommendationRequest:
    return RecommendationRequest(
        chat_messages=[ChatMessage(role="user", content="팀은 FastAPI 기반 LLM 서비스를 만듭니다.")],
        team_profile=team_profile,
        draft_profile=draft_profile,
        team_report="팀은 FastAPI 기반 LLM 추천 서비스를 준비하고 있습니다.",
        ready_for_recommendation=True,
        collection_status="ready",
        current_matching_status="운영진 확인 필요",
        top_k=1,
        prefilter_top_n=10,
    )


@pytest.mark.asyncio
async def test_create_recommendation_runs_pipeline(monkeypatch, team_profile: TeamProfile, mentor: Mentor):
    calls: list[str] = []
    expected_team_profile = team_profile
    candidate = CandidateResult(
        mentor_id=1,
        rank=1,
        reason="기술 스택이 적합합니다.",
        weak_point="일정 확인이 필요합니다.",
    )
    combination = CombCandidateResult(
        mentor_id=1,
        candidate_ids=[],
        strengths=[],
        weak_points=[],
        rank=1,
        reason="기술 스택이 적합합니다.",
        weak_point="일정 확인이 필요합니다.",
    )
    report = RecommendationReport(
        team_summary="팀 요약",
        confidence_basis="근거",
        candidate_summary="후보 요약",
        combinations=[],
        final_recommendation="최종 추천",
        cautions=[],
        generated_at="2026-05-12T00:00:00+00:00",
    )

    async def fake_get_mentor_candidates(*, team_profile: TeamProfile, top_k: int, prefilter_top_n: int | None):
        calls.append("candidates")
        assert top_k == 1
        assert prefilter_top_n == 10
        return [candidate]

    async def fake_generate(self, team_profile: TeamProfile, candidates: list[CandidateResult]):
        calls.append("combinations")
        assert team_profile == expected_team_profile
        assert candidates == [candidate]
        return [combination]

    async def fake_generate_report(request):
        calls.append("report")
        assert request.team_profile == expected_team_profile
        assert request.candidates == [candidate]
        assert request.combinations == [combination]
        assert request.mentors == [mentor]
        return report

    monkeypatch.setattr("app.modules.recommendation.service.get_all_mentors", lambda: [mentor])
    monkeypatch.setattr("app.modules.recommendation.service.get_mentor_candidates", fake_get_mentor_candidates)
    monkeypatch.setattr("app.modules.recommendation.service.CombinationGeneratorService.generate", fake_generate)
    monkeypatch.setattr("app.modules.recommendation.service.generate_report", fake_generate_report)

    response = await create_recommendation(recommendation_request(expected_team_profile))

    assert calls == ["candidates", "combinations", "report"]
    assert response.team_profile == expected_team_profile
    assert response.candidates == [candidate]
    assert response.combinations == [combination]
    assert response.mentors == [mentor]
    assert response.recommendation_report == report


@pytest.mark.asyncio
async def test_create_recommendation_rejects_draft_only_profile(team_profile: TeamProfile):
    with pytest.raises(RecommendationNotReadyError, match="팀 프로필"):
        await create_recommendation(recommendation_request(None, draft_profile=team_profile))


@pytest.mark.asyncio
async def test_create_recommendation_rejects_not_ready(team_profile: TeamProfile):
    request = recommendation_request(team_profile)
    request.ready_for_recommendation = False

    with pytest.raises(RecommendationNotReadyError, match="준비"):
        await create_recommendation(request)


@pytest.mark.asyncio
async def test_create_recommendation_rejects_missing_team_profile():
    with pytest.raises(RecommendationNotReadyError, match="팀 프로필"):
        await create_recommendation(recommendation_request(None))


@pytest.mark.asyncio
async def test_create_recommendation_rejects_collecting_status(team_profile: TeamProfile):
    request = recommendation_request(team_profile)
    request.collection_status = "collecting"

    with pytest.raises(RecommendationNotReadyError, match="준비"):
        await create_recommendation(request)


@pytest.mark.asyncio
async def test_create_recommendation_rejects_unknown_candidate(monkeypatch, team_profile: TeamProfile, mentor: Mentor):
    async def fake_get_mentor_candidates(*, team_profile: TeamProfile, top_k: int, prefilter_top_n: int | None):
        return [
            CandidateResult(
                mentor_id=999,
                rank=1,
                reason="기술 스택이 적합합니다.",
                weak_point="일정 확인이 필요합니다.",
            )
        ]

    monkeypatch.setattr("app.modules.recommendation.service.get_all_mentors", lambda: [mentor])
    monkeypatch.setattr("app.modules.recommendation.service.get_mentor_candidates", fake_get_mentor_candidates)

    with pytest.raises(UnknownCandidateMentorError) as exc_info:
        await create_recommendation(recommendation_request(team_profile))

    assert exc_info.value.missing_ids == [999]
