"""공통 pytest 픽스처. 모든 테스트에서 공유."""
import os

# 실제 API 호출 없이 테스트하도록 더미 키 사전 설정
os.environ.setdefault("UPSTAGE_API_KEY", "test-mock-key")
os.environ.setdefault("GITHUB_PAT", "test-mock-pat")
os.environ.setdefault("NOTION_TOKEN", "test-notion-token")
os.environ.setdefault("MAX_REFINE_ITER", "3")
os.environ.setdefault("SCORE_THRESHOLD", "90")

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.repo import RepoContext
from src.models.story import Section, StoryDraft, Verdict, SectionScore
from src.services.session_manager import manager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_orchestrator():
    """실제 LLM 호출 없이 오케스트레이터 start_session 모킹."""
    with patch("src.services.orchestrator.start_session") as mock:
        yield mock


@pytest.fixture
def mock_repo_ctx():
    return RepoContext(
        owner="testuser",
        name="test-repo",
        description="테스트용 레포지토리",
        readme="# Test Repo\n\nFastAPI 기반 테스트 프로젝트.",
        commits=[],
    )


@pytest.fixture
def mock_section_problem():
    return Section(
        name="problem",
        title="문제 인식",
        content="기존 포트폴리오 작성 방식은 수동으로 많은 시간이 소요됩니다. " * 15,
    )


@pytest.fixture
def mock_section_status():
    return Section(
        name="status",
        title="현황 파악",
        content="FastAPI와 LangGraph를 사용하여 백엔드 파이프라인을 구성했습니다. " * 10,
    )


@pytest.fixture
def mock_section_cause():
    return Section(
        name="cause",
        title="원인 분석 및 해결책",
        content="LLM 기반 에이전트가 레포 컨텍스트를 분석하여 자동으로 섹션을 생성합니다. " * 10,
    )


@pytest.fixture
def mock_section_result():
    return Section(
        name="result",
        title="결과 정리 및 성능 향상",
        content="자동화로 포트폴리오 작성 시간이 90% 단축되었습니다. " * 10,
    )


@pytest.fixture
def mock_draft(mock_section_problem, mock_section_status, mock_section_cause, mock_section_result):
    return StoryDraft(
        problem=mock_section_problem,
        status=mock_section_status,
        cause=mock_section_cause,
        result=mock_section_result,
        architecture="```mermaid\ngraph TD\n  A[Client] --> B[FastAPI]\n```",
        dataflow="```mermaid\nsequenceDiagram\n  Client->>API: POST /session\n```",
        merged="## 최종 포트폴리오\n\n" + "내용 " * 200,
    )


@pytest.fixture
def mock_verdict():
    return Verdict(
        scores=[
            SectionScore(name="problem", score=92, rationale="명확한 문제 정의"),
            SectionScore(name="status", score=88, rationale="기술 스택 적절히 서술"),
            SectionScore(name="cause", score=91, rationale="원인 분석 논리적"),
            SectionScore(name="result", score=95, rationale="구체적인 성과 제시"),
        ],
        weakest="status",
        overall_pass=True,
    )


@pytest.fixture
def global_session():
    """전역 SessionManager에 세션 생성 (오케스트레이터 노드 테스트용)."""
    s = manager().create(repo_url="https://github.com/test/repo")
    return s
