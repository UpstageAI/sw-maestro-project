from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile


def test_combinations_endpoint_returns_generated_combinations(monkeypatch):
    team_profile = TeamProfile(
        skills="Python, FastAPI",
        members_rnr="리더(BE), 팀원(FE)",
        project_plan_tech_goals="LLM 서비스 구축",
        maestro_program_goals="소마 인증",
        mentoring_needs="아키텍처 리뷰",
    )
    candidates = [
        CandidateResult(
            mentor_id=1,
            rank=1,
            reason="기술 스택이 적합합니다.",
            weak_point="일정 확인이 필요합니다.",
        )
    ]

    async def fake_generate(self, request_team_profile, request_candidates):
        assert request_team_profile == team_profile
        assert request_candidates == candidates
        return [
            CombCandidateResult(
                mentor_id=1,
                candidate_ids=[],
                strengths=[],
                weak_points=[],
                rank=1,
                reason="기술 스택이 적합합니다.",
                weak_point="일정 확인이 필요합니다.",
            )
        ]

    mentors = [
        Mentor(
            mentor_id=1,
            name="테스트멘토",
            stacks=["Python"],
            hobbie="",
            target="기술",
            is_overseas=False,
            is_new_mentor=False,
            can_plan=True,
            meeting_mode_preference="온라인",
            domains=["AI"],
            is_certificated=False,
            career=[("테스트회사", 5)],
        )
    ]

    monkeypatch.setattr("app.modules.combination_generator.router.get_all_mentors", lambda: mentors)
    monkeypatch.setattr("app.modules.combination_generator.router.CombinationGeneratorService.generate", fake_generate)

    response = TestClient(app).post(
        "/api/combinations",
        json={
            "team_profile": team_profile.model_dump(mode="json"),
            "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        },
    )

    assert response.status_code == 200
    assert response.json()["combinations"][0]["mentor_id"] == 1
