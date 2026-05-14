from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


ROOT = Path(__file__).resolve().parents[1]


def read_source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_homepage_serves_react_shell_assets_and_icon(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="root"' in response.text
    assert "/assets/index-" in response.text
    assert "<script " in response.text
    assert "<style>" not in response.text
    assert "demo" not in response.text.lower()
    assert "데모" not in response.text

    asset_paths = [
        part.split('"')[0]
        for part in response.text.split('href="')[1:]
        if part.startswith("/assets/")
    ] + [
        part.split('"')[0]
        for part in response.text.split('src="')[1:]
        if part.startswith("/assets/")
    ]
    assert asset_paths
    for asset_path in asset_paths:
        assert client.get(asset_path).status_code == 200

    icon_response = client.get("/favicon.ico")
    assert icon_response.status_code == 200
    assert "image/svg+xml" in icon_response.headers["content-type"]
    assert b"<svg" in icon_response.content


def test_frontend_studio_tabs_sources_search_and_progress_contract():
    app_source = read_source("frontend/src/App.tsx")
    source_panel_source = read_source("frontend/src/components/SourceTabPanel.tsx")
    source_panel_config = read_source("frontend/src/lib/source-panel.ts")
    graph_source = read_source("frontend/src/components/KnowledgeGraphPanel.tsx")
    flow_source = read_source("frontend/src/components/LangGraphFlowPanel.tsx")
    obsidian_graph_source = read_source("frontend/src/components/ObsidianGraphPanel.tsx")
    combined_frontend_source = app_source + source_panel_source + source_panel_config

    for expected in [
        'type StudioTab = "graph" | "source" | "search" | "workspace"',
        'activeStudioTab === "graph"',
        'activeStudioTab === "source"',
        'activeStudioTab === "search"',
        'activeStudioTab === "workspace"',
        'from "@/components/SourceTabPanel"',
        'from "@/lib/source-panel"',
        "refreshWorkspaceAfterIngestion",
        'startIngestionProgress("Source")',
        'startIngestionProgress("File")',
        "/documents/source",
        "/documents/upload",
        "/search/llm",
        "/search?q=",
        "llm-search-form",
    ]:
        assert expected in app_source

    for expected in [
        'source_type: "txt"',
        "신규 기능 아이디어 문서",
        "ingestionFlowSteps",
        "serverIngestionStepIds",
        "Validate input",
        "SQLite persist",
        "Fetch graph payload",
        "Render update",
    ]:
        assert expected in source_panel_config

    for expected in [
        "Multi-source ingestion",
        "source-ingestion-form",
        "[field-sizing:fixed]",
        ".pdf,.csv",
        "Manual Card",
        "Create Card",
    ]:
        assert expected in combined_frontend_source

    for expected in [
        'setIngestionStep("refreshWorkspace")',
        'setIngestionStep("refreshDocuments")',
        'setIngestionStep("refreshCards")',
        'setIngestionStep("refreshGraph")',
        'setIngestionStep("refreshWorkflows")',
        'setIngestionStep("render")',
    ]:
        assert expected in app_source

    assert "function SourceConsole" not in app_source
    assert "function ManualCardConsole" not in app_source
    assert "function IngestionFlowProgress" not in app_source
    assert "function SourceConsole" in source_panel_source
    assert "function ManualCardConsole" in source_panel_source
    assert "function IngestionFlowProgress" in source_panel_source

    assert "onPointerDown" in graph_source
    assert "onPointerMove" in graph_source
    assert 'addEventListener("wheel"' in graph_source
    assert "graph-studio-zoom-in" in graph_source
    assert "graph-studio-reset-view" in graph_source
    assert "visibleLinks.length" in graph_source
    assert "onWheel" in obsidian_graph_source
    assert "requestAnimationFrame" in obsidian_graph_source
    assert "visibleLinks.map" in obsidian_graph_source
    assert "input_contract" in flow_source
    assert "output_contract" in flow_source


def test_load_samples_resets_database_to_curated_demo_workspace():
    app_source = read_source("frontend/src/App.tsx")
    samples_source = read_source("frontend/src/lib/samples.ts")

    for expected in [
        "Sample workspace reset",
        "existingWorkspaces",
        "for (const workspace of existingWorkspaces)",
        'method: "DELETE"',
        "ICH Demo Workspace",
    ]:
        assert expected in app_source
    assert "Sample sources saved" not in app_source

    for expected in [
        "demo:strategy:architecture",
        "demo:mentor:feedback",
        "demo:engineering:intake",
        "demo:engineering:performance",
        "demo:search:grounded-llm",
        "demo:ux:workflow",
        "GraphDB",
        "SQLite relation",
        "relation linking",
        "중복 카드",
        "근거 기반 답변",
    ]:
        assert expected in samples_source
