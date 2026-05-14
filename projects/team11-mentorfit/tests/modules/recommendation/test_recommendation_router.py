from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile
from app.modules.report.schemas import RecommendationReport


def make_team_profile() -> TeamProfile:
    return TeamProfile(
        members_rnr="리더는 백엔드, 팀원은 프론트엔드를 담당합니다.",
        project_plan_tech_goals="LLM 기반 멘토 추천 서비스를 구축합니다.",
        mentoring_needs="아키텍처 리뷰와 추천 품질 개선 피드백이 필요합니다.",
        fit_conditions="AI 서비스 운영 경험이 있는 멘토를 선호합니다.",
        maestro_program_goals="인증",
        skills="Python, FastAPI",
    )


def make_mentor() -> Mentor:
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


def make_payload(team_profile: TeamProfile | None = None) -> dict:
    profile = team_profile or make_team_profile()
    return {
        "chat_messages": [{"role": "user", "content": "팀은 FastAPI 기반 LLM 서비스를 만듭니다."}],
        "team_profile": profile.model_dump(mode="json"),
        "draft_profile": profile.model_dump(mode="json"),
        "team_report": "팀은 FastAPI 기반 LLM 추천 서비스를 준비하고 있습니다.",
        "ready_for_recommendation": True,
        "collection_status": "ready",
        "current_matching_status": "운영진 확인 필요",
        "top_k": 1,
        "prefilter_top_n": 10,
    }


def test_recommendations_endpoint_returns_pipeline_result(monkeypatch):
    team_profile = make_team_profile()
    mentor = make_mentor()
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

    async def fake_get_mentor_candidates(*, team_profile: TeamProfile, top_k: int, prefilter_top_n: int | None):
        return [candidate]

    async def fake_generate(self, team_profile: TeamProfile, candidates: list[CandidateResult]):
        return [combination]

    async def fake_generate_report(request):
        return RecommendationReport(
            team_summary="팀 요약",
            confidence_basis="근거",
            candidate_summary="후보 요약",
            combinations=[],
            final_recommendation="최종 추천",
            cautions=[],
            generated_at="2026-05-12T00:00:00+00:00",
        )

    monkeypatch.setattr("app.modules.recommendation.service.get_all_mentors", lambda: [mentor])
    monkeypatch.setattr("app.modules.recommendation.service.get_mentor_candidates", fake_get_mentor_candidates)
    monkeypatch.setattr("app.modules.recommendation.service.CombinationGeneratorService.generate", fake_generate)
    monkeypatch.setattr("app.modules.recommendation.service.generate_report", fake_generate_report)

    response = TestClient(app).post("/api/recommendations", json=make_payload(team_profile))

    assert response.status_code == 200
    data = response.json()
    assert data["team_profile"]["skills"] == "Python, FastAPI"
    assert data["candidates"][0]["mentor_id"] == 1
    assert data["combinations"][0]["mentor_id"] == 1
    assert data["mentors"][0]["name"] == "테스트멘토"
    assert data["recommendation_report"]["team_summary"] == "팀 요약"


def test_recommendations_endpoint_rejects_not_ready():
    payload = make_payload()
    payload["ready_for_recommendation"] = False

    response = TestClient(app).post("/api/recommendations", json=payload)

    assert response.status_code == 409
    assert "준비" in response.json()["detail"]


def test_recommendations_endpoint_validates_bounds():
    payload = make_payload()
    payload["top_k"] = 0

    response = TestClient(app).post("/api/recommendations", json=payload)

    assert response.status_code == 422


def test_recommendations_endpoint_rejects_costly_top_k():
    payload = make_payload()
    payload["top_k"] = 20

    response = TestClient(app).post("/api/recommendations", json=payload)

    assert response.status_code == 422


def test_recommendations_endpoint_rejects_unknown_candidate(monkeypatch):
    async def fake_get_mentor_candidates(*, team_profile: TeamProfile, top_k: int, prefilter_top_n: int | None):
        return [
            CandidateResult(
                mentor_id=999,
                rank=1,
                reason="기술 스택이 적합합니다.",
                weak_point="일정 확인이 필요합니다.",
            )
        ]

    monkeypatch.setattr("app.modules.recommendation.service.get_all_mentors", lambda: [make_mentor()])
    monkeypatch.setattr("app.modules.recommendation.service.get_mentor_candidates", fake_get_mentor_candidates)

    response = TestClient(app).post("/api/recommendations", json=make_payload())

    assert response.status_code == 422
    assert "999" in response.json()["detail"]
