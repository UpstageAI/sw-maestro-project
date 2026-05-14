"""오케스트레이터 추가 노드 통합 테스트 — Issue 3 해결."""
import pytest
from unittest.mock import patch, MagicMock

from src.services.session_manager import manager, State
from src.models.story import Section, SectionScore, Verdict, StoryDraft
from src.models.repo import RepoContext


@pytest.fixture
def session():
    return manager().create(repo_url="https://github.com/test/repo")


@pytest.fixture
def mock_ctx():
    return RepoContext(
        owner="testuser",
        name="testrepo",
        readme="# 테스트",
        commits=[],
    )


def _make_draft():
    return StoryDraft(
        problem=Section(name="problem", title="문제 인식", content="내용" * 50),
        status=Section(name="status", title="현황 파악", content="내용" * 40),
        cause=Section(name="cause", title="원인 분석", content="내용" * 50),
        result=Section(name="result", title="결과 정리", content="내용" * 40),
    )


# ──────────────────────────────────────────────
# compress_node
# ──────────────────────────────────────────────

class TestCompressNode:
    @patch("src.services.context_builder.invoke")
    def test_compress_node_calls_compress(self, mock_invoke, session, mock_ctx):
        from src.services.orchestrator import compress_node
        mock_invoke.return_value = "압축 요약 결과"
        state = {"session_id": session.id, "repo_ctx": mock_ctx}
        result = compress_node(state)
        assert "repo_ctx" in result

    @patch("src.services.context_builder.invoke")
    def test_compress_node_sets_state(self, mock_invoke, session, mock_ctx):
        from src.services.orchestrator import compress_node
        mock_invoke.return_value = "요약"
        compress_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert session.state == State.COMPRESSING

    @patch("src.services.context_builder.invoke")
    def test_compress_node_updates_ctx_on_session(self, mock_invoke, session, mock_ctx):
        from src.services.orchestrator import compress_node
        mock_invoke.return_value = "요약"
        compress_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert session.ctx is not None


# ──────────────────────────────────────────────
# interview_node
# ──────────────────────────────────────────────

class TestInterviewNode:
    @patch("src.agents.interview_agent.run")
    def test_interview_node_returns_questions(self, mock_run, session, mock_ctx):
        from src.services.orchestrator import interview_node
        mock_run.return_value = ["질문1", "질문2"]
        state = {"session_id": session.id, "repo_ctx": mock_ctx}
        result = interview_node(state)
        assert result["questions"] == ["질문1", "질문2"]

    @patch("src.agents.interview_agent.run")
    def test_interview_node_sets_state(self, mock_run, session, mock_ctx):
        from src.services.orchestrator import interview_node
        mock_run.return_value = []
        interview_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert session.state == State.INTERVIEWING

    @patch("src.agents.interview_agent.run")
    def test_interview_node_stores_questions_on_session(self, mock_run, session, mock_ctx):
        from src.services.orchestrator import interview_node
        mock_run.return_value = ["Q1", "Q2", "Q3"]
        interview_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert session.questions == ["Q1", "Q2", "Q3"]

    @patch("src.agents.interview_agent.run")
    def test_interview_node_no_questions(self, mock_run, session, mock_ctx):
        from src.services.orchestrator import interview_node
        mock_run.return_value = []
        result = interview_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert result["questions"] == []


# ──────────────────────────────────────────────
# merge_answers_node — wait_for_answers_node
# ──────────────────────────────────────────────

class TestWaitForAnswersNode:
    def test_no_questions_returns_empty_answers(self, session):
        from src.services.orchestrator import wait_for_answers_node
        state = {"session_id": session.id, "questions": []}
        result = wait_for_answers_node(state)
        assert result == {"answers": []}

    def test_no_questions_key_returns_empty(self, session):
        from src.services.orchestrator import wait_for_answers_node
        state = {"session_id": session.id}
        result = wait_for_answers_node(state)
        assert result == {"answers": []}


# ──────────────────────────────────────────────
# diagram_node
# ──────────────────────────────────────────────

class TestDiagramNode:
    @patch("src.agents.architecture_agent.run")
    @patch("src.agents.dataflow_agent.run")
    def test_diagram_node_returns_both_diagrams(self, mock_df, mock_arch, session, mock_ctx):
        from src.services.orchestrator import diagram_node
        mock_arch.return_value = "```mermaid\ngraph TD\n  A-->B\n```"
        mock_df.return_value = "```mermaid\nsequenceDiagram\n  A->>B: call\n```"
        result = diagram_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert "architecture" in result
        assert "dataflow" in result

    @patch("src.agents.architecture_agent.run")
    @patch("src.agents.dataflow_agent.run")
    def test_diagram_node_sets_diagramming_state(self, mock_df, mock_arch, session, mock_ctx):
        from src.services.orchestrator import diagram_node
        mock_arch.return_value = "arch"
        mock_df.return_value = "dataflow"
        diagram_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert session.state == State.DIAGRAMMING

    @patch("src.agents.architecture_agent.run")
    @patch("src.agents.dataflow_agent.run")
    def test_diagram_node_stores_on_draft(self, mock_df, mock_arch, session, mock_ctx):
        from src.services.orchestrator import diagram_node
        mock_arch.return_value = "아키텍처 다이어그램"
        mock_df.return_value = "데이터플로우"
        diagram_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert session.draft.architecture == "아키텍처 다이어그램"
        assert session.draft.dataflow == "데이터플로우"


# ──────────────────────────────────────────────
# merge_node
# ──────────────────────────────────────────────

class TestMergeNode:
    def _make_state(self, session_id, ctx):
        draft = _make_draft()
        return {
            "session_id": session_id,
            "repo_ctx": ctx,
            "problem": draft.problem,
            "status": draft.status,
            "cause": draft.cause,
            "result": draft.result,
            "architecture": "arch",
            "dataflow": "df",
            "verdict": Verdict(
                scores=[SectionScore(name="problem", score=92, rationale="우수")],
                overall_pass=True,
                weakest="problem",
            ),
            "iter_n": 1,
        }

    @patch("src.agents.merge_agent.run")
    def test_merge_node_returns_merged(self, mock_merge, session, mock_ctx):
        from src.services.orchestrator import merge_node
        mock_merge.return_value = "# 최종 포트폴리오\n\n내용" * 100
        result = merge_node(self._make_state(session.id, mock_ctx))
        assert "merged" in result

    @patch("src.agents.merge_agent.run")
    def test_merge_node_sets_ready_for_template_state(self, mock_merge, session, mock_ctx):
        from src.services.orchestrator import merge_node
        mock_merge.return_value = "최종 내용"
        merge_node(self._make_state(session.id, mock_ctx))
        assert session.state == State.READY_FOR_TEMPLATE

    @patch("src.agents.merge_agent.run")
    def test_merge_node_stores_cost_report(self, mock_merge, session, mock_ctx):
        from src.services.orchestrator import merge_node
        mock_merge.return_value = "최종 내용"
        merge_node(self._make_state(session.id, mock_ctx))
        assert isinstance(session.cost_report, dict)


# ──────────────────────────────────────────────
# generate_node — ThreadPoolExecutor 모킹
# ──────────────────────────────────────────────

class TestGenerateNode:
    @patch("src.services.orchestrator.SECTION_AGENTS")
    def test_generate_node_produces_four_sections(self, mock_agents, session, mock_ctx):
        from src.services.orchestrator import generate_node
        for name in ["problem", "status", "cause", "result"]:
            mock_agents[name] = MagicMock(
                return_value=Section(name=name, title="제목", content="내용" * 30)
            )
        state = {"session_id": session.id, "repo_ctx": mock_ctx}
        result = generate_node(state)
        assert "problem" in result
        assert "status" in result
        assert "cause" in result
        assert "result" in result

    @patch("src.services.orchestrator.SECTION_AGENTS")
    def test_generate_node_sets_generating_state(self, mock_agents, session, mock_ctx):
        from src.services.orchestrator import generate_node
        for name in ["problem", "status", "cause", "result"]:
            mock_agents[name] = MagicMock(
                return_value=Section(name=name, title="제목", content="내용" * 30)
            )
        generate_node({"session_id": session.id, "repo_ctx": mock_ctx})
        assert session.state == State.GENERATING


# ──────────────────────────────────────────────
# refine_node
# ──────────────────────────────────────────────

class TestRefineNode:
    @patch("src.services.orchestrator.SECTION_AGENTS")
    def test_refine_node_refines_from_weakest(self, mock_agents, session, mock_ctx):
        from src.services.orchestrator import refine_node
        for name in ["problem", "status", "cause", "result"]:
            mock_agents[name] = MagicMock(
                return_value=Section(name=name, title="재생성", content="재생성 내용" * 30)
            )
        state = {
            "session_id": session.id,
            "repo_ctx": mock_ctx,
            "verdict": Verdict(
                scores=[SectionScore(name="cause", score=70, rationale="미흡")],
                overall_pass=False,
                weakest="cause",
            ),
            "iter_n": 1,
        }
        result = refine_node(state)
        # cause 이후 섹션 (cause, result) 재생성
        assert "cause" in result or "result" in result
