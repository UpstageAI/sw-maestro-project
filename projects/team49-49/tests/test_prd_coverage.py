from pathlib import Path

from app.main import create_app
from app.models.schemas import CARD_STATUSES, CARD_TYPES, CONFIDENCE_LEVELS, RELATION_TYPES
from app.repositories.sqlite import SQLiteRepository


def test_prd_constants_are_available():
    assert set(CARD_TYPES) == {
        "idea",
        "problem",
        "target_user",
        "hypothesis",
        "evidence",
        "decision",
        "risk",
        "feature",
        "question",
    }
    assert set(CARD_STATUSES) == {"proposed", "needs_validation", "validated", "rejected", "decided", "needs_review"}
    assert set(CONFIDENCE_LEVELS) == {"low", "medium", "high"}
    assert set(RELATION_TYPES) == {"supports", "contradicts", "duplicates", "related_to", "derived_from"}


def test_prd_routes_are_registered(tmp_path):
    app = create_app(repository=SQLiteRepository(tmp_path / "ich.sqlite3"))
    methods_by_path: dict[str, set[str]] = {}
    for route in app.routes:
        methods = getattr(route, "methods", None) or set()
        methods_by_path.setdefault(route.path, set()).update(methods)

    paths = set(methods_by_path)
    assert "/" in paths
    assert "/health" in paths
    assert "/api/workspaces" in paths
    assert "/api/workspaces/{workspace_id}" in paths
    assert "/api/workspaces/{workspace_id}/documents/text" in paths
    assert "/api/workspaces/{workspace_id}/documents/upload" in paths
    assert "/api/workspaces/{workspace_id}/documents" in paths
    assert "/api/workspaces/{workspace_id}/cards" in paths
    assert "/api/workspaces/{workspace_id}/cards/{card_id}" in paths
    assert "/api/workspaces/{workspace_id}/cards/{card_id}/relations" in paths
    assert "/api/workspaces/{workspace_id}/cards/{card_id}/paths" in paths
    assert "/api/workspaces/{workspace_id}/search" in paths
    assert "/api/workspaces/{workspace_id}/qa" in paths
    assert "/api/workspaces/{workspace_id}/qa/history" in paths
    assert "/api/workspaces/{workspace_id}/graph" in paths
    assert "/api/workflows" in paths

    assert {"PATCH", "DELETE"} <= methods_by_path["/api/workspaces/{workspace_id}"]
    assert {"POST"} <= methods_by_path["/api/workspaces/{workspace_id}/cards"]
    assert {"DELETE"} <= methods_by_path["/api/workspaces/{workspace_id}/cards/{card_id}"]


def test_app_initializes_source_connector_registry(tmp_path):
    app = create_app(repository=SQLiteRepository(tmp_path / "ich.sqlite3"))

    assert {"notion", "github", "slack", "linear", "mcp", "web"} <= set(app.state.source_connector_registry)


def test_readme_documents_local_mvp_usage():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "지원 입력 형식" in readme
    assert "사용 흐름" in readme
    assert "개인정보" in readme
    assert "API 요약" in readme
    assert "환경 변수" in readme
    assert "유료 API Key 없이" in readme
    assert "LangGraph 붙이는 방식" in readme


def test_prd_reflects_current_post_planning_decisions():
    prd = Path("docs/PRD.md").read_text(encoding="utf-8")

    assert "codex_oauth" in prd
    assert "Claude" in prd
    assert "Upstage" in prd
    assert "Obsidian-like graph" in prd
    assert "ICH_CHROMA_PATH" not in prd
    assert "Gemini" not in prd
    assert "Do not delete cards in MVP" not in prd
    assert "DELETE /api/workspaces/{workspace_id}" in prd
    assert "DELETE /api/workspaces/{workspace_id}/cards/{card_id}" in prd
    assert "POST /api/workspaces/{workspace_id}/cards" in prd
    assert "PATCH /api/workspaces/{workspace_id}" in prd
    assert "Coaching Feedback Compliance" in prd
    assert "Demo Readiness" in prd
    assert "score-ranked top-N" in prd
