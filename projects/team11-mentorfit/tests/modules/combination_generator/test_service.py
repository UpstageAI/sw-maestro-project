from __future__ import annotations

import json

import pytest

from app.modules.combination_generator.service import CombinationGeneratorService
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile

SAMPLE_MENTORS = [
    Mentor(
        mentor_id=1,
        name="멘토1",
        stacks=["Python", "LLM"],
        hobbie="",
        target="기술",
        is_overseas=False,
        is_new_mentor=False,
        can_plan=False,
        meeting_mode_preference="온·오프라인",
        domains=["AI"],
        is_certificated=False,
        career=[("AI 스타트업", 5)],
    ),
    Mentor(
        mentor_id=2,
        name="멘토2",
        stacks=["React", "TypeScript"],
        hobbie="",
        target="기술",
        is_overseas=False,
        is_new_mentor=False,
        can_plan=False,
        meeting_mode_preference="온라인",
        domains=["프론트엔드"],
        is_certificated=False,
        career=[("네이버", 6)],
    ),
    Mentor(
        mentor_id=3,
        name="멘토3",
        stacks=["Java", "Spring"],
        hobbie="",
        target="기술",
        is_overseas=False,
        is_new_mentor=False,
        can_plan=False,
        meeting_mode_preference="오프라인",
        domains=["백엔드"],
        is_certificated=False,
        career=[("쿠팡", 10)],
    ),
]

SAMPLE_CANDIDATES = [
    CandidateResult(
        mentor_id=1,
        rank=1,
        reason="LLM 전문가라 팀 프로젝트에 적합",
        weak_point="프론트엔드 경험 부족",
    ),
    CandidateResult(
        mentor_id=2,
        rank=2,
        reason="프론트엔드 보완 가능",
        weak_point="LLM 경험 부족",
    ),
    CandidateResult(
        mentor_id=3,
        rank=3,
        reason="백엔드 보완 가능",
        weak_point="프론트엔드 경험 부족",
    ),
]

TEAM_PROFILE = TeamProfile(
    skills="Python, React",
    members_rnr="리더(BE), 팀원(FE)",
    project_plan_tech_goals="LLM 서비스 구축",
    maestro_program_goals="소마 인증",
    mentoring_needs="아키텍처 리뷰",
)

MOCK_LLM_RESPONSE = json.dumps({
    "second_mentor_id": 2,
    "third_mentor_id": 3,
    "strengths": ["강점1", "강점2", "강점3", "초과"],
    "weak_points": ["약점1", "약점2", "약점3", "초과"],
    "reason": "세 멘토가 팀의 기술 스택을 고루 커버함",
})


@pytest.mark.asyncio
async def test_generate_returns_n_combinations(monkeypatch):
    async def mock_chat(messages, model="solar-pro"):
        return MOCK_LLM_RESPONSE

    monkeypatch.setattr(
        "app.modules.combination_generator.service.upstage_client.chat_completion",
        mock_chat,
    )
    monkeypatch.setattr("app.modules.combination_generator.service.settings.mock_mode", False)
    monkeypatch.setattr("app.modules.combination_generator.service.settings.upstage_api_key", "test")

    service = CombinationGeneratorService(mentors=SAMPLE_MENTORS)
    results = await service.generate(TEAM_PROFILE, SAMPLE_CANDIDATES[:1])

    assert len(results) == 1
    assert results[0].mentor_id == 1
    assert results[0].rank == 1


@pytest.mark.asyncio
async def test_base_mentor_excluded_from_candidate_ids(monkeypatch):
    async def mock_chat(messages, model="solar-pro"):
        return MOCK_LLM_RESPONSE

    monkeypatch.setattr(
        "app.modules.combination_generator.service.upstage_client.chat_completion",
        mock_chat,
    )
    monkeypatch.setattr("app.modules.combination_generator.service.settings.mock_mode", False)
    monkeypatch.setattr("app.modules.combination_generator.service.settings.upstage_api_key", "test")

    service = CombinationGeneratorService(mentors=SAMPLE_MENTORS)
    results = await service.generate(TEAM_PROFILE, SAMPLE_CANDIDATES[:1])

    assert 1 not in results[0].candidate_ids
    assert results[0].candidate_ids == [2, 3]
    assert len(results[0].strengths) == 3
    assert len(results[0].weak_points) == 3


@pytest.mark.asyncio
async def test_parse_failure_returns_partial_result(monkeypatch):
    async def mock_chat(messages, model="solar-pro"):
        return "invalid json {"

    monkeypatch.setattr(
        "app.modules.combination_generator.service.upstage_client.chat_completion",
        mock_chat,
    )
    monkeypatch.setattr("app.modules.combination_generator.service.settings.mock_mode", False)
    monkeypatch.setattr("app.modules.combination_generator.service.settings.upstage_api_key", "test")

    service = CombinationGeneratorService(mentors=SAMPLE_MENTORS)
    results = await service.generate(TEAM_PROFILE, SAMPLE_CANDIDATES[:1])

    assert len(results) == 1
    assert results[0].candidate_ids == []
    assert results[0].strengths == []
    assert results[0].weak_points == []
    assert results[0].reason == "LLM 전문가라 팀 프로젝트에 적합"


@pytest.mark.asyncio
async def test_mock_mode_uses_candidate_pool_as_supplements(monkeypatch):
    monkeypatch.setattr("app.modules.combination_generator.service.settings.mock_mode", True)

    service = CombinationGeneratorService(mentors=SAMPLE_MENTORS)
    results = await service.generate(TEAM_PROFILE, SAMPLE_CANDIDATES)

    assert results[0].candidate_ids == [2, 3]
