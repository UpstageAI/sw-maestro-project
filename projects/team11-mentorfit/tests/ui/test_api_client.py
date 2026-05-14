from __future__ import annotations

import httpx
import pytest

from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile
from app.modules.team_profile.schemas import ChatMessage
from ui import api_client


@pytest.fixture
def team_profile() -> TeamProfile:
    return TeamProfile(
        skills="Python, FastAPI",
        members_rnr="리더(BE), 팀원(FE)",
        project_plan_tech_goals="LLM 서비스 구축",
        maestro_program_goals="소마 인증",
        mentoring_needs="아키텍처 리뷰",
    )


@pytest.fixture
def candidate() -> CandidateResult:
    return CandidateResult(
        mentor_id=1,
        rank=1,
        reason="기술 스택이 적합합니다.",
        weak_point="일정 확인이 필요합니다.",
    )


@pytest.fixture
def mentor() -> Mentor:
    return Mentor(
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


@pytest.mark.asyncio
async def test_create_team_profile_from_prompt_parses_response(monkeypatch, team_profile: TeamProfile):
    async def fake_request_json(method: str, path: str, *, json=None):
        assert method == "POST"
        assert path == "/api/team-profile/prompt"
        assert json["prompt"] == "팀 정보"
        return {
            "team_profile": team_profile.model_dump(mode="json"),
            "team_report": "팀 리포트",
            "chat_messages": [{"role": "user", "content": "팀 정보"}],
            "llm_used": False,
            "draft_profile": team_profile.model_dump(mode="json"),
            "missing_fields": [],
            "next_question": None,
            "ready_for_recommendation": True,
            "status": "ready",
        }

    monkeypatch.setattr(api_client, "_request_json", fake_request_json)

    response = await api_client.create_team_profile_from_prompt("팀 정보", [])

    assert response.ready_for_recommendation is True
    assert response.chat_messages == [ChatMessage(role="user", content="팀 정보")]


@pytest.mark.asyncio
async def test_create_report_parses_response(
    monkeypatch,
    team_profile: TeamProfile,
    candidate: CandidateResult,
    mentor: Mentor,
):
    combination = CombCandidateResult(
        mentor_id=1,
        candidate_ids=[],
        strengths=[],
        weak_points=[],
        rank=1,
        reason="기술 스택이 적합합니다.",
        weak_point="일정 확인이 필요합니다.",
    )

    async def fake_request_json(method: str, path: str, *, json=None):
        assert method == "POST"
        assert path == "/api/report"
        assert json["mentors"][0]["name"] == "테스트멘토"
        return {
            "team_summary": "팀 요약",
            "confidence_basis": "근거",
            "candidate_summary": "후보 요약",
            "combinations": [],
            "final_recommendation": "최종 추천",
            "cautions": [],
            "generated_at": "2026-05-10T00:00:00+00:00",
        }

    monkeypatch.setattr(api_client, "_request_json", fake_request_json)

    report = await api_client.create_report(team_profile, "팀 리포트", [candidate], [combination], [mentor], None)

    assert report.team_summary == "팀 요약"


@pytest.mark.asyncio
async def test_request_json_turns_status_error_into_api_error(monkeypatch):
    request = httpx.Request("GET", "http://test/api")
    response = httpx.Response(500, json={"detail": "서버 오류"}, request=request)

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, json=None):
            return response

    monkeypatch.setattr(api_client.httpx, "AsyncClient", FakeClient)

    with pytest.raises(api_client.MentorFitApiError, match="서버 오류"):
        await api_client._request_json("GET", "/api/test")


@pytest.mark.asyncio
async def test_create_candidates_wraps_invalid_response(monkeypatch, team_profile: TeamProfile):
    async def fake_request_json(method: str, path: str, *, json=None):
        return [{"mentor_id": 1, "rank": 0, "reason": "bad", "weak_point": "bad"}]

    monkeypatch.setattr(api_client, "_request_json", fake_request_json)

    with pytest.raises(api_client.MentorFitApiError, match="응답 형식"):
        await api_client.create_mentor_candidates(team_profile, 1, 10)
