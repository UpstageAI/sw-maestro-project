"""publish / export-pdf 엔드포인트 통합 테스트 — 누락 커버리지 보완."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.main import app
from src.services.session_manager import manager, State
from src.models.story import Section, StoryDraft
from src.models.repo import RepoContext

client = TestClient(app)


@pytest.fixture
def ready_session(mock_draft, mock_repo_ctx):
    """READY_FOR_TEMPLATE 상태의 세션 반환."""
    with patch("src.services.orchestrator.start_session"):
        res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        sid = res.json()["session_id"]
    s = manager().get(sid)
    s.set_state(State.READY_FOR_TEMPLATE)
    s.draft = mock_draft
    s.ctx = mock_repo_ctx
    return s


# ──────────────────────────────────────────────
# POST /api/session/{sid}/publish
# ──────────────────────────────────────────────

class TestPublishEndpoint:
    def test_publish_wrong_state_returns_400(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        res = client.post(f"/api/session/{sid}/publish", json={"template_id": "star"})
        assert res.status_code == 400

    def test_publish_nonexistent_session_returns_404(self):
        res = client.post("/api/session/nonexistent/publish", json={"template_id": "star"})
        assert res.status_code == 404

    def test_publish_success(self, ready_session, tmp_path):
        sid = ready_session.id
        mock_result = {"success": True, "page_url": "https://notion.so/page-123", "backup_path": str(tmp_path / "test.md")}
        with patch("src.services.orchestrator.publish_session") as mock_pub:
            mock_pub.side_effect = lambda s, tid: setattr(s, "publish_result", mock_result) or setattr(s, "state", State.DONE)
            res = client.post(f"/api/session/{sid}/publish", json={"template_id": "star"})
        assert res.status_code == 200
        assert res.json()["ok"] is True

    def test_publish_updates_notion_token(self, ready_session):
        sid = ready_session.id
        with patch("src.services.orchestrator.publish_session"):
            client.post(f"/api/session/{sid}/publish", json={
                "template_id": "star",
                "notion_token": "new-token",
            })
        assert ready_session.notion_token == "new-token"

    def test_publish_updates_parent_page_id(self, ready_session):
        sid = ready_session.id
        with patch("src.services.orchestrator.publish_session"):
            client.post(f"/api/session/{sid}/publish", json={
                "template_id": "star",
                "notion_parent_page_id": "new-page-id",
            })
        assert ready_session.notion_parent_page_id == "new-page-id"


# ──────────────────────────────────────────────
# POST /api/session/{sid}/export-pdf
# ──────────────────────────────────────────────

class TestExportPdfEndpoint:
    def test_export_pdf_wrong_state_returns_400(self, mock_orchestrator):
        sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
        res = client.post(f"/api/session/{sid}/export-pdf", json={"template_id": "star"})
        assert res.status_code == 400

    def test_export_pdf_nonexistent_session_returns_404(self):
        res = client.post("/api/session/nonexistent/export-pdf", json={"template_id": "star"})
        assert res.status_code == 404

    def test_export_pdf_invalid_template_returns_400(self, ready_session):
        sid = ready_session.id
        res = client.post(f"/api/session/{sid}/export-pdf", json={"template_id": "invalid_template"})
        assert res.status_code == 400

    def test_export_pdf_success(self, ready_session, tmp_path):
        sid = ready_session.id
        fake_path = tmp_path / "test_output.pdf"
        fake_path.write_bytes(b"%PDF-1.4")
        with patch("src.services.pdf_publisher.render_pdf", return_value=fake_path):
            res = client.post(f"/api/session/{sid}/export-pdf", json={"template_id": "star"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["filename"] == "test_output.pdf"

    def test_export_pdf_render_failure_returns_error_json(self, ready_session):
        sid = ready_session.id
        with patch("src.services.pdf_publisher.render_pdf", side_effect=Exception("렌더링 실패")):
            res = client.post(f"/api/session/{sid}/export-pdf", json={"template_id": "star"})
        assert res.status_code == 200  # 예외를 JSON으로 반환 (전파 안 함)
        data = res.json()
        assert data["success"] is False
        assert "error" in data

    def test_export_pdf_done_state_allowed(self, ready_session):
        """DONE 상태에서도 export-pdf 허용."""
        ready_session.set_state(State.DONE)
        sid = ready_session.id
        with patch("src.services.pdf_publisher.render_pdf", side_effect=Exception("test")):
            res = client.post(f"/api/session/{sid}/export-pdf", json={"template_id": "star"})
        # DONE 상태면 400이 아닌 200 (with error) 반환
        assert res.status_code == 200
