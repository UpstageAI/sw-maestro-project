"""오케스트레이터 노드 및 로직 통합 테스트 — LLM 호출 없음."""
import pytest
from unittest.mock import patch, MagicMock

from src.services.session_manager import manager, State
from src.models.story import Section, SectionScore, Verdict, StoryDraft
from src import config


@pytest.fixture
def session():
    """전역 manager에 세션 생성 — 오케스트레이터 노드가 manager()로 조회하므로 필수."""
    return manager().create(repo_url="https://github.com/test/repo")


# ──────────────────────────────────────────────
# should_refine 조건 분기 테스트 (순수 함수 — 모킹 불필요)
# ──────────────────────────────────────────────

class TestShouldRefine:
    def test_returns_diagram_when_overall_pass(self):
        from src.services.orchestrator import should_refine
        verdict = MagicMock(overall_pass=True)
        state = {"verdict": verdict, "iter_n": 1}
        assert should_refine(state) == "diagram"

    def test_returns_refine_when_fail_and_under_limit(self):
        from src.services.orchestrator import should_refine
        verdict = MagicMock(overall_pass=False)
        state = {"verdict": verdict, "iter_n": 0}
        assert should_refine(state) == "refine"

    def test_returns_diagram_when_max_iter_reached(self):
        from src.services.orchestrator import should_refine
        verdict = MagicMock(overall_pass=False)
        state = {"verdict": verdict, "iter_n": config.MAX_REFINE_ITER}
        assert should_refine(state) == "diagram"

    def test_returns_diagram_when_iter_exceeds_max(self):
        from src.services.orchestrator import should_refine
        verdict = MagicMock(overall_pass=False)
        state = {"verdict": verdict, "iter_n": config.MAX_REFINE_ITER + 5}
        assert should_refine(state) == "diagram"

    def test_iter_n_one_below_max_returns_refine(self):
        from src.services.orchestrator import should_refine
        verdict = MagicMock(overall_pass=False)
        state = {"verdict": verdict, "iter_n": config.MAX_REFINE_ITER - 1}
        assert should_refine(state) == "refine"


# ──────────────────────────────────────────────
# Abort 체크 테스트
# ──────────────────────────────────────────────

class TestAbortCheck:
    def test_aborted_session_raises_on_node_entry(self, session):
        from src.services.orchestrator import fetch_node
        session.request_abort("테스트 중단")
        with pytest.raises(RuntimeError, match="aborted"):
            fetch_node({"session_id": session.id, "repo_url": session.repo_url})

    def test_non_aborted_session_proceeds_to_fn(self, session):
        from src.services.orchestrator import fetch_node
        mock_ctx = MagicMock(full_name="test/repo", user_attached_info=None)
        with patch("src.services.github_loader.fetch_repo", return_value=mock_ctx), \
             patch("src.services.context_builder.sanitize_files", return_value=mock_ctx):
            result = fetch_node({"session_id": session.id, "repo_url": session.repo_url})
        assert "repo_ctx" in result


# ──────────────────────────────────────────────
# fetch_node 테스트
# ──────────────────────────────────────────────

class TestFetchNode:
    def test_fetch_node_sets_fetching_state(self, session):
        from src.services.orchestrator import fetch_node
        mock_ctx = MagicMock(full_name="test/repo", user_attached_info=None)
        with patch("src.services.github_loader.fetch_repo", return_value=mock_ctx), \
             patch("src.services.context_builder.sanitize_files", return_value=mock_ctx):
            fetch_node({"session_id": session.id, "repo_url": session.repo_url})
        assert session.state == State.FETCHING

    def test_fetch_node_returns_repo_ctx(self, session):
        from src.services.orchestrator import fetch_node
        mock_ctx = MagicMock(full_name="test/repo", user_attached_info=None)
        with patch("src.services.github_loader.fetch_repo", return_value=mock_ctx), \
             patch("src.services.context_builder.sanitize_files", return_value=mock_ctx):
            result = fetch_node({"session_id": session.id, "repo_url": session.repo_url})
        assert result["repo_ctx"] is mock_ctx

    def test_fetch_node_attaches_user_info(self, session):
        from src.services.orchestrator import fetch_node
        mock_ctx = MagicMock(full_name="test/repo", user_attached_info=None)
        with patch("src.services.github_loader.fetch_repo", return_value=mock_ctx), \
             patch("src.services.context_builder.sanitize_files", return_value=mock_ctx):
            fetch_node({
                "session_id": session.id,
                "repo_url": session.repo_url,
                "user_attached_info": "추가 정보",
            })
        assert mock_ctx.user_attached_info == "추가 정보"


# ──────────────────────────────────────────────
# validate_node 테스트
# ──────────────────────────────────────────────

class TestValidateNode:
    def _make_state(self, session_id, iter_n=0):
        return {
            "session_id": session_id,
            "history": [],
            "iter_n": iter_n,
            "problem": Section(name="problem", title="문제 인식", content="문제 내용" * 20),
            "status": Section(name="status", title="현황 파악", content="현황 내용" * 15),
            "cause": Section(name="cause", title="원인 분석", content="원인 내용" * 20),
            "result": Section(name="result", title="결과 정리", content="결과 내용" * 15),
        }

    def test_validate_node_increments_iter_n(self, session):
        from src.services.orchestrator import validate_node
        mock_verdict = Verdict(
            scores=[SectionScore(name="problem", score=95, rationale="우수")],
            overall_pass=True, weakest="problem",
        )
        with patch("src.agents.validator_agent.run", return_value=mock_verdict):
            result = validate_node(self._make_state(session.id, iter_n=0))
        assert result["iter_n"] == 1

    def test_validate_node_accumulates_history(self, session):
        from src.services.orchestrator import validate_node
        mock_verdict = Verdict(
            scores=[SectionScore(name="problem", score=80, rationale="양호")],
            overall_pass=False, weakest="problem",
        )
        with patch("src.agents.validator_agent.run", return_value=mock_verdict):
            state = self._make_state(session.id, iter_n=0)
            state["history"] = [mock_verdict]  # 이미 1회 있음
            result = validate_node(state)
        assert len(result["history"]) == 2

    def test_validate_node_stores_verdict_on_session(self, session):
        from src.services.orchestrator import validate_node
        mock_verdict = Verdict(
            scores=[SectionScore(name="status", score=91, rationale="좋음")],
            overall_pass=True, weakest="status",
        )
        with patch("src.agents.validator_agent.run", return_value=mock_verdict):
            validate_node(self._make_state(session.id))
        assert session.verdict is mock_verdict

    def test_validate_node_sets_validating_state(self, session):
        from src.services.orchestrator import validate_node
        mock_verdict = Verdict(
            scores=[SectionScore(name="cause", score=88, rationale="명확")],
            overall_pass=True, weakest="cause",
        )
        with patch("src.agents.validator_agent.run", return_value=mock_verdict):
            validate_node(self._make_state(session.id))
        assert session.state == State.VALIDATING


# ──────────────────────────────────────────────
# merge_answers_node 테스트
# ──────────────────────────────────────────────

class TestMergeAnswersNode:
    def test_empty_answers_returns_no_update(self, session, mock_repo_ctx):
        from src.services.orchestrator import merge_answers_node
        state = {
            "session_id": session.id,
            "repo_ctx": mock_repo_ctx,
            "questions": ["질문1"],
            "answers": [""],
        }
        result = merge_answers_node(state)
        assert result == {}

    def test_answers_merged_into_context(self, session, mock_repo_ctx):
        from src.services.orchestrator import merge_answers_node
        state = {
            "session_id": session.id,
            "repo_ctx": mock_repo_ctx,
            "questions": ["이 프로젝트의 주요 기능은?"],
            "answers": ["AI 기반 포트폴리오 자동 생성"],
        }
        result = merge_answers_node(state)
        assert "repo_ctx" in result
        assert "AI 기반 포트폴리오 자동 생성" in result["repo_ctx"].user_attached_info

    def test_existing_user_info_preserved(self, session, mock_repo_ctx):
        from src.services.orchestrator import merge_answers_node
        mock_repo_ctx.user_attached_info = "기존 정보"
        state = {
            "session_id": session.id,
            "repo_ctx": mock_repo_ctx,
            "questions": ["질문"],
            "answers": ["새 답변입니다"],
        }
        result = merge_answers_node(state)
        ctx = result["repo_ctx"]
        assert "기존 정보" in ctx.user_attached_info
        assert "새 답변입니다" in ctx.user_attached_info
