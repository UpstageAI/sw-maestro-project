from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile
from app.modules.report.schemas import ReportGenerationRequest
from app.modules.report.service import build_report_combinations, generate_report, parse_report_response


@pytest.fixture
def mentors() -> list[Mentor]:
    return [
        Mentor(
            mentor_id=1,
            name="메인멘토",
            stacks=["Python", "LLM"],
            hobbie="",
            target="기술",
            is_overseas=False,
            is_new_mentor=False,
            can_plan=True,
            meeting_mode_preference="온·오프라인",
            domains=["AI"],
            is_certificated=False,
            career=[("AI 스타트업", 5)],
        ),
        Mentor(
            mentor_id=2,
            name="보완멘토A",
            stacks=["React"],
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
            name="보완멘토B",
            stacks=["Spring"],
            hobbie="",
            target="기술",
            is_overseas=False,
            is_new_mentor=False,
            can_plan=False,
            meeting_mode_preference="오프라인",
            domains=["백엔드"],
            is_certificated=True,
            career=[("쿠팡", 10)],
        ),
    ]


@pytest.fixture
def report_request(mentors: list[Mentor]) -> ReportGenerationRequest:
    return ReportGenerationRequest(
        team_profile=TeamProfile(
            skills="Python, React",
            members_rnr="리더(BE), 팀원(FE)",
            project_plan_tech_goals="LLM 서비스 구축",
            maestro_program_goals="소마 인증",
            mentoring_needs="아키텍처 리뷰",
        ),
        team_report="팀은 LLM 기반 서비스 구현과 프론트엔드 완성도가 모두 중요합니다.",
        candidates=[
            CandidateResult(
                mentor_id=1,
                rank=1,
                reason="LLM과 Python 경험이 직접적으로 적합합니다.",
                weak_point="프론트엔드 경험은 제한적입니다.",
            )
        ],
        combinations=[
            CombCandidateResult(
                mentor_id=1,
                candidate_ids=[2, 3],
                strengths=["AI", "프론트엔드", "백엔드", "초과"],
                weak_points=["일정 확인 필요", "도메인 검증 필요", "팀 선호 확인 필요", "초과"],
                rank=1,
                reason="세 멘토가 역할을 나눠 보완합니다.",
                weak_point="메인 멘토의 프론트엔드 경험은 제한적입니다.",
            )
        ],
        mentors=mentors,
        current_matching_status="매칭 현황은 수동 확인 필요",
    )


def test_report_generation_request_validates(report_request: ReportGenerationRequest):
    assert report_request.team_profile.skills == "Python, React"
    assert report_request.combinations[0].candidate_ids == [2, 3]


def test_build_report_combinations_maps_mentor_ids(report_request: ReportGenerationRequest):
    combinations = build_report_combinations(report_request)

    assert combinations[0].main_mentor.name == "메인멘토"
    assert [mentor.name for mentor in combinations[0].supplement_mentors] == ["보완멘토A", "보완멘토B"]
    assert len(combinations[0].strengths) == 3
    assert len(combinations[0].weak_points) == 3


def test_report_generation_request_rejects_missing_mentor_id(report_request: ReportGenerationRequest):
    data = report_request.model_dump()
    data["mentors"] = [report_request.mentors[0].model_dump()]

    with pytest.raises(ValidationError, match="멘토 ID"):
        ReportGenerationRequest.model_validate(data)


def test_report_endpoint_rejects_missing_mentor_id(report_request: ReportGenerationRequest):
    data = report_request.model_dump()
    data["mentors"] = [report_request.mentors[0].model_dump()]

    response = TestClient(app).post("/api/report", json=data)

    assert response.status_code == 422


def test_parse_report_response_success(report_request: ReportGenerationRequest):
    combinations = build_report_combinations(report_request)
    raw = json.dumps({
        "team_summary": "팀 요약",
        "confidence_basis": "신뢰도 근거",
        "candidate_summary": "후보 요약",
        "final_recommendation": "최종 추천",
        "cautions": ["주의"],
    })

    report = parse_report_response(raw, combinations)

    assert report.team_summary == "팀 요약"
    assert report.combinations == combinations
    assert report.cautions == ["주의"]


def test_parse_report_response_failure(report_request: ReportGenerationRequest):
    combinations = build_report_combinations(report_request)

    with pytest.raises(json.JSONDecodeError):
        parse_report_response("not-json", combinations)


@pytest.mark.asyncio
async def test_generate_report_mock_mode(monkeypatch, report_request: ReportGenerationRequest):
    monkeypatch.setattr("app.modules.report.service.settings.mock_mode", True)

    report = await generate_report(report_request)

    assert report.combinations[0].main_mentor.name == "메인멘토"
    assert "참고 자료" in report.cautions[0]


def test_report_endpoint_returns_report(monkeypatch, report_request: ReportGenerationRequest):
    monkeypatch.setattr("app.modules.report.service.settings.mock_mode", True)

    response = TestClient(app).post("/api/report", json=report_request.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert data["combinations"][0]["main_mentor"]["name"] == "메인멘토"
    assert "recommended_combinations" not in data


def test_sample_report_loader_removed():
    import app.modules.report.service as service

    assert not hasattr(service, "load_sample_report")
