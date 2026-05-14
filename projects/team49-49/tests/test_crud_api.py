import warnings

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


def test_workspace_crud_api_and_openapi_schema(tmp_path):
    app = create_app(repository=SQLiteRepository(tmp_path / "ich.sqlite3"))
    client = TestClient(app)

    created = client.post(
        "/api/workspaces",
        json={"name": "CRUD Workspace", "description": "initial"},
    )
    assert created.status_code == 201
    workspace_id = created.json()["id"]

    updated = client.patch(
        f"/api/workspaces/{workspace_id}",
        json={"name": "Renamed Workspace", "description": "updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed Workspace"
    assert updated.json()["description"] == "updated"

    fetched = client.get(f"/api/workspaces/{workspace_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Renamed Workspace"

    deleted = client.delete(f"/api/workspaces/{workspace_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/workspaces/{workspace_id}").status_code == 404
    assert all(item["id"] != workspace_id for item in client.get("/api/workspaces").json())

    openapi = client.get("/openapi.json").json()
    workspace_path = openapi["paths"]["/api/workspaces/{workspace_id}"]
    assert {"get", "patch", "delete"} <= set(workspace_path)
    assert "WorkspaceRead" in openapi["components"]["schemas"]
    assert "WorkspaceUpdate" in openapi["components"]["schemas"]


def test_card_crud_api_enforces_workspace_scope_and_openapi_schema(tmp_path):
    app = create_app(repository=SQLiteRepository(tmp_path / "ich.sqlite3"))
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "Cards"}).json()["id"]
    other_workspace_id = client.post("/api/workspaces", json={"name": "Other"}).json()["id"]

    created = client.post(
        f"/api/workspaces/{workspace_id}/cards",
        json={
            "card_type": "decision",
            "title": "SQLite 우선",
            "summary": "MVP에서는 SQLite를 우선 사용한다.",
            "evidence_quote": "결정: MVP에서는 SQLite를 우선 사용한다.",
            "keywords": ["SQLite", "MVP"],
            "tags": ["decided"],
            "status": "decided",
            "confidence": "high",
        },
    )
    assert created.status_code == 201
    card = created.json()
    card_id = card["id"]
    assert card["workspace_id"] == workspace_id
    assert card["source_document_id"]
    assert card["source_chunk_id"]

    assert client.get(f"/api/workspaces/{workspace_id}/cards/{card_id}").status_code == 200
    assert client.get(f"/api/workspaces/{other_workspace_id}/cards/{card_id}").status_code == 404

    updated = client.patch(
        f"/api/workspaces/{workspace_id}/cards/{card_id}",
        json={
            "card_type": "hypothesis",
            "title": "회의 준비 가설",
            "summary": "출처와 상태를 같이 보여주면 준비 시간이 줄어든다.",
            "evidence_quote": "가설: 출처와 상태를 같이 보여주면 준비 시간이 줄어든다.",
            "keywords": ["회의", "출처"],
            "tags": ["needs_validation"],
            "status": "needs_validation",
            "confidence": "medium",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["card_type"] == "hypothesis"
    assert updated.json()["title"] == "회의 준비 가설"
    assert updated.json()["keywords"] == ["회의", "출처"]

    listed = client.get(f"/api/workspaces/{workspace_id}/cards", params={"card_type": "hypothesis"}).json()
    assert [item["id"] for item in listed] == [card_id]

    deleted = client.delete(f"/api/workspaces/{workspace_id}/cards/{card_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/workspaces/{workspace_id}/cards/{card_id}").status_code == 404

    openapi = client.get("/openapi.json").json()
    cards_path = openapi["paths"]["/api/workspaces/{workspace_id}/cards"]
    card_path = openapi["paths"]["/api/workspaces/{workspace_id}/cards/{card_id}"]
    assert {"get", "post"} <= set(cards_path)
    assert {"get", "patch", "delete"} <= set(card_path)
    assert "KnowledgeCardCreateRequest" in openapi["components"]["schemas"]
    assert "KnowledgeCardUpdate" in openapi["components"]["schemas"]
    assert "KnowledgeCardRead" in openapi["components"]["schemas"]


def test_source_document_crud_reindexes_cards_and_openapi_schema(tmp_path):
    app = create_app(repository=SQLiteRepository(tmp_path / "ich.sqlite3"))
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"name": "Sources"}).json()["id"]
    other_workspace_id = client.post("/api/workspaces", json={"name": "Other"}).json()["id"]

    created = client.post(
        f"/api/workspaces/{workspace_id}/documents/source",
        json={
            "source_type": "manual",
            "source_url": "",
            "external_id": "manual:demo",
            "title": "demo-source",
            "content": "결정: 첫 원문에서 결정 카드를 만든다.",
        },
    )
    assert created.status_code == 201
    document_id = created.json()["document_id"]
    assert created.json()["card_count"] == 1

    document = client.get(f"/api/workspaces/{workspace_id}/documents/{document_id}").json()
    assert document["filename"] == "demo-source.md"
    assert document["document_type"] == "md"
    assert client.get(f"/api/workspaces/{other_workspace_id}/documents/{document_id}").status_code == 404

    updated = client.patch(
        f"/api/workspaces/{workspace_id}/documents/{document_id}",
        json={
            "filename": "edited-source",
            "source_type": "web",
            "source_url": "https://example.com/edited-source",
            "external_id": "web:edited",
            "content": "가설: 수정된 원문을 저장하면 가설 카드로 다시 추출된다.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["filename"] == "edited-source.md"
    assert updated.json()["source_type"] == "web"
    assert updated.json()["content"].startswith("가설:")

    cards = client.get(f"/api/workspaces/{workspace_id}/cards").json()
    assert len(cards) == 1
    assert cards[0]["source_document_id"] == document_id
    assert cards[0]["card_type"] == "hypothesis"
    assert "수정된 원문" in cards[0]["summary"]

    deleted = client.delete(f"/api/workspaces/{workspace_id}/documents/{document_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/workspaces/{workspace_id}/documents/{document_id}").status_code == 404
    assert client.get(f"/api/workspaces/{workspace_id}/cards").json() == []

    openapi = client.get("/openapi.json").json()
    document_path = openapi["paths"]["/api/workspaces/{workspace_id}/documents/{document_id}"]
    assert {"get", "patch", "delete"} <= set(document_path)
    assert "RawDocumentRead" in openapi["components"]["schemas"]
    assert "RawDocumentUpdate" in openapi["components"]["schemas"]


def test_openapi_operation_ids_are_unique(tmp_path):
    app = create_app(repository=SQLiteRepository(tmp_path / "ich.sqlite3"))
    client = TestClient(app)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        openapi = client.get("/openapi.json").json()
    operation_ids = [
        operation["operationId"]
        for path_item in openapi["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "patch", "delete", "put"}
    ]

    assert not [warning for warning in caught if "Duplicate Operation ID" in str(warning.message)]
    assert len(operation_ids) == len(set(operation_ids))
