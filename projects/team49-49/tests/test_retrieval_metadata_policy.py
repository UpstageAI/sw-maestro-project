from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository
from app.services.retrieval import RetrievalService


def _seed_workspace(repository: SQLiteRepository) -> dict:
    repository.initialize()
    workspace = repository.create_workspace("Retrieval Filters")
    notion_doc = repository.create_raw_document(
        workspace_id=workspace["id"],
        filename="notion.md",
        document_type="md",
        content="결정: notion 원문에서 추출.",
        source_type="notion",
        source_url="https://notion.so/x",
        external_id="notion-x",
    )
    web_doc = repository.create_raw_document(
        workspace_id=workspace["id"],
        filename="web.md",
        document_type="md",
        content="결정: web 원문에서 추출.",
        source_type="web",
        source_url="https://web/x",
        external_id="web-x",
    )
    notion_chunk = repository.create_chunks(
        document_id=notion_doc["id"],
        workspace_id=workspace["id"],
        contents=["결정: notion 원문에서 추출."],
    )[0]
    web_chunk = repository.create_chunks(
        document_id=web_doc["id"],
        workspace_id=workspace["id"],
        contents=["결정: web 원문에서 추출."],
    )[0]
    notion_card = repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=notion_doc["id"],
        source_chunk_id=notion_chunk["id"],
        card_type="decision",
        title="Notion 결정 카드",
        summary="Notion에서 정리한 결정.",
        evidence_quote="결정: notion 원문에서 추출.",
        keywords=["notion", "결정"],
        tags=[],
        status="decided",
        confidence="high",
    )
    web_card = repository.create_knowledge_card(
        workspace_id=workspace["id"],
        source_document_id=web_doc["id"],
        source_chunk_id=web_chunk["id"],
        card_type="evidence",
        title="Web 근거 카드",
        summary="웹에서 정리한 근거.",
        evidence_quote="결정: web 원문에서 추출.",
        keywords=["web", "근거"],
        tags=[],
        status="validated",
        confidence="medium",
    )
    return {
        "workspace": workspace,
        "notion_card": notion_card,
        "web_card": web_card,
    }


def test_retrieval_filters_cards_by_metadata_first_pass(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    seed = _seed_workspace(repository)
    service = RetrievalService(repository)

    result = service.search(
        workspace_id=seed["workspace"]["id"],
        query="결정",
        filters={"card_type": "decision"},
    )

    assert {card["id"] for card in result["cards"]} == {seed["notion_card"]["id"]}


def test_retrieval_filters_cards_by_source_type(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    seed = _seed_workspace(repository)
    service = RetrievalService(repository)

    result = service.search(
        workspace_id=seed["workspace"]["id"],
        query="근거",
        filters={"source_type": "web"},
    )

    assert {card["id"] for card in result["cards"]} == {seed["web_card"]["id"]}
    assert all(chunk.get("source_type") == "web" for chunk in result["chunks"])


def test_retrieval_metadata_tiebreak_prefers_matching_metadata(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    seed = _seed_workspace(repository)
    service = RetrievalService(repository)

    result = service.search(
        workspace_id=seed["workspace"]["id"],
        query="결정",
        filters={"source_type": "notion"},
    )

    assert result["cards"]
    assert result["cards"][0]["id"] == seed["notion_card"]["id"]


def test_search_api_exposes_metadata_filters(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    _seed_workspace(repository)
    app = create_app(repository=repository)
    client = TestClient(app)
    workspace_id = client.get("/api/workspaces").json()[0]["id"]

    response = client.get(
        f"/api/workspaces/{workspace_id}/search",
        params={"q": "결정", "card_type": "decision", "source_type": "notion"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cards"]
    assert {card["card_type"] for card in body["cards"]} == {"decision"}
    assert all(card.get("source_type") == "notion" for card in body["cards"])
