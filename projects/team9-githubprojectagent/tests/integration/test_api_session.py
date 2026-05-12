"""세션 API 통합 테스트 — FastAPI TestClient 사용, LLM 호출 없음."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.main import app
from src.services.session_manager import manager, State

client = TestClient(app)


# ──────────────────────────────────────────────
# POST /api/session
# ──────────────────────────────────────────────

class TestCreateSession:
    def test_success_returns_session_id(self, mock_orchestrator):
        res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        assert res.status_code == 200
        body = res.json()
        assert "session_id" in body
        assert len(body["session_id"]) == 12

    def test_orchestrator_called_on_create(self, mock_orchestrator):
        client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        mock_orchestrator.assert_called_once()

    def test_empty_url_returns_400(self):
        res = client.post("/api/session", json={"repo_url": "   "})
        assert res.status_code == 400
        assert "repo_url" in res.json()["detail"]

    def test_missing_url_returns_422(self):
        res = client.post("/api/session", json={})
        assert res.status_code == 422

    def test_with_optional_pat(self, mock_orchestrator):
        res = client.post("/api/session", json={
            "repo_url": "https://github.com/a/private-repo",
            "pat": "ghp_testtoken1234567890",
        })
        assert res.status_code == 200

    def test_with_user_attached_info(self, mock_orchestrator):
        res = client.post("/api/session", json={
            "repo_url": "https://github.com/a/b",
            "user_attached_info": "이 프로젝트는 FastAPI 기반입니다.",
        })
        assert res.status_code == 200

    def test_with_notion_fields(self, mock_orchestrator):
        res = client.post("/api/session", json={
            "repo_url": "https://github.com/a/b",
            "notion_token": "secret-notion-token",
            "notion_parent_page_id": "page-abc123",
        })
        assert res.status_code == 200

    def test_multiple_sessions_have_unique_ids(self, mock_orchestrator):
        ids = set()
        for _ in range(5):
            res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
            ids.add(res.json()["session_id"])
        assert len(ids) == 5


# ──────────────────────────────────────────────
# GET /api/session/{sid}
# ──────────────────────────────────────────────

class TestGetSession:
    def test_returns_200_for_existing_session(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        res = client.get(f"/api/session/{sid}")
        assert res.status_code == 200

    def test_response_has_required_fields(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        data = client.get(f"/api/session/{sid}").json()
        for field in ["id", "state", "state_age_sec", "elapsed_sec", "log", "questions",
                      "answers", "draft", "verdict", "history", "cost", "error", "repo_url"]:
            assert field in data, f"필드 누락: {field}"

    def test_id_matches_session_id(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        data = client.get(f"/api/session/{sid}").json()
        assert data["id"] == sid

    def test_repo_url_matches(self, mock_orchestrator):
        url = "https://github.com/testuser/testrepo"
        sid = client.post("/api/session", json={"repo_url": url}).json()["session_id"]
        data = client.get(f"/api/session/{sid}").json()
        assert data["repo_url"] == url

    def test_nonexistent_session_returns_404(self):
        res = client.get("/api/session/nonexistent123")
        assert res.status_code == 404

    def test_log_is_list(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        data = client.get(f"/api/session/{sid}").json()
        assert isinstance(data["log"], list)

    def test_elapsed_sec_is_non_negative(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        data = client.get(f"/api/session/{sid}").json()
        assert data["elapsed_sec"] >= 0

    def test_draft_has_all_section_keys(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        data = client.get(f"/api/session/{sid}").json()
        for key in ["problem", "status", "cause", "result", "architecture", "dataflow", "merged"]:
            assert key in data["draft"], f"draft 키 누락: {key}"


# ──────────────────────────────────────────────
# POST /api/session/{sid}/abort
# ──────────────────────────────────────────────

class TestAbortSession:
    def test_abort_existing_session_returns_ok(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        res = client.post(f"/api/session/{sid}/abort")
        assert res.status_code == 200
        assert res.json()["ok"] is True

    def test_abort_updates_state_to_aborted(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        client.post(f"/api/session/{sid}/abort")
        s = manager().get(sid)
        assert s.state == State.ABORTED

    def test_abort_nonexistent_session_returns_404(self):
        res = client.post("/api/session/nonexistent123/abort")
        assert res.status_code == 404


# ──────────────────────────────────────────────
# POST /api/session/{sid}/answers
# ──────────────────────────────────────────────

class TestSubmitAnswers:
    def test_wrong_state_returns_400(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        # 초기 상태(INIT)에서 답변 제출 시도
        res = client.post(f"/api/session/{sid}/answers", json={"answers": ["답변1"]})
        assert res.status_code == 400

    def test_count_mismatch_returns_400(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        # 세션을 INTERVIEWING 상태로 전환하고 질문 2개 설정
        s = manager().get(sid)
        s.set_state(State.INTERVIEWING)
        s.questions = ["질문1", "질문2"]
        # 답변 1개만 제출
        res = client.post(f"/api/session/{sid}/answers", json={"answers": ["답변1"]})
        assert res.status_code == 400

    def test_nonexistent_session_returns_404(self):
        res = client.post("/api/session/nonexistent/answers", json={"answers": []})
        assert res.status_code == 404

    def test_correct_answers_count_accepted(self, mock_orchestrator):
        with patch("src.services.orchestrator.submit_answers"):
            sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
            s = manager().get(sid)
            s.set_state(State.INTERVIEWING)
            s.questions = ["질문1", "질문2"]
            res = client.post(f"/api/session/{sid}/answers", json={"answers": ["답1", "답2"]})
            assert res.status_code == 200
            assert res.json()["ok"] is True


# ──────────────────────────────────────────────
# GET /api/session/{sid}/templates
# ──────────────────────────────────────────────

class TestGetTemplates:
    def test_wrong_state_returns_400(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        res = client.get(f"/api/session/{sid}/templates")
        assert res.status_code == 400

    def test_ready_for_template_state_returns_templates(self, mock_orchestrator, mock_draft, mock_repo_ctx):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        s = manager().get(sid)
        s.set_state(State.READY_FOR_TEMPLATE)
        s.draft = mock_draft
        s.ctx = mock_repo_ctx  # template preview_md에서 ctx.full_name 사용
        res = client.get(f"/api/session/{sid}/templates")
        assert res.status_code == 200
        data = res.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)
        assert len(data["templates"]) > 0

    def test_templates_have_required_fields(self, mock_orchestrator, mock_draft, mock_repo_ctx):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        s = manager().get(sid)
        s.set_state(State.READY_FOR_TEMPLATE)
        s.draft = mock_draft
        s.ctx = mock_repo_ctx
        templates = client.get(f"/api/session/{sid}/templates").json()["templates"]
        for t in templates:
            assert "id" in t
            assert "name" in t
            assert "description" in t

    def test_nonexistent_session_returns_404(self):
        res = client.get("/api/session/nonexistent/templates")
        assert res.status_code == 404


# ──────────────────────────────────────────────
# GET /api/session/{sid}/download/{filename}
# ──────────────────────────────────────────────

class TestDownloadArtifact:
    def test_nonexistent_session_returns_404(self):
        res = client.get("/api/session/nonexistent/download/test.pdf")
        assert res.status_code == 404

    def test_path_traversal_attempt_blocked(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        # ../를 포함한 path traversal 시도
        res = client.get(f"/api/session/{sid}/download/../../etc/passwd")
        # 파일이 없으면 404, 방어 코드로 인해 404 반환
        assert res.status_code == 404

    def test_nonexistent_file_returns_404(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        res = client.get(f"/api/session/{sid}/download/nonexistent_file.pdf")
        assert res.status_code == 404


# ──────────────────────────────────────────────
# GET /health
# ──────────────────────────────────────────────

class TestHealthEndpoint:
    def test_returns_200(self):
        res = client.get("/health")
        assert res.status_code == 200

    def test_ok_is_true(self):
        assert client.get("/health").json()["ok"] is True

    def test_has_model_field(self):
        assert "model" in client.get("/health").json()

    def test_has_score_threshold(self):
        assert "score_threshold" in client.get("/health").json()

    def test_has_effort_fields(self):
        data = client.get("/health").json()
        assert "effort_fast" in data
        assert "effort_deep" in data

    def test_has_max_refine_iter(self):
        assert "max_refine_iter" in client.get("/health").json()


# ──────────────────────────────────────────────
# GET / 및 GET /app
# ──────────────────────────────────────────────

class TestStaticPages:
    def test_index_returns_200(self):
        res = client.get("/")
        assert res.status_code == 200

    def test_app_page_returns_200(self):
        res = client.get("/app")
        assert res.status_code == 200
