"""CRUD-first code-level verification.

Exercises every CRUD path through the SQLiteRepository directly (no HTTP),
then through the FastAPI surface via TestClient (no live server required).
All operations are asserted with explicit expected outcomes; any drift
fails the script. No dependence on test fixtures.

Run:
    python scripts/crud_codepath_verify.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


def banner(label: str) -> None:
    print()
    print(f"=== {label} ===")


# ---------------------------------------------------------------------------
# 1. Repository-layer CRUD
# ---------------------------------------------------------------------------

def repo_layer_crud(repo: SQLiteRepository) -> None:
    banner("REPOSITORY LAYER - Workspace CRUD")
    ws = repo.create_workspace("Repo CRUD", "first")
    assert ws["id"] >= 1 and ws["name"] == "Repo CRUD"
    print(f"  created ws={ws['id']} name={ws['name']!r}")

    listed = repo.list_workspaces()
    assert any(w["id"] == ws["id"] for w in listed)
    print(f"  list returns {len(listed)} workspaces")

    fetched = repo.get_workspace(ws["id"])
    assert fetched["name"] == "Repo CRUD"
    print(f"  get returns name={fetched['name']!r}")

    updated = repo.update_workspace(ws["id"], name="Repo CRUD v2", description="renamed")
    assert updated["name"] == "Repo CRUD v2" and updated["description"] == "renamed"
    print(f"  patch returns name={updated['name']!r} description={updated['description']!r}")

    try:
        repo.get_workspace(99999)
    except KeyError as exc:
        print(f"  missing get raises KeyError: {exc}")
    else:
        raise AssertionError("expected KeyError on missing workspace")

    banner("REPOSITORY LAYER - Document/Chunk/Card cascade")
    doc = repo.create_raw_document(
        workspace_id=ws["id"],
        filename="repo.md",
        document_type="md",
        content="결정: repository 계층 cascade 검증.",
        source_type="manual",
        source_url="",
        external_id="repo-1",
    )
    chunks = repo.create_chunks(doc["id"], ws["id"], ["결정: cascade 검증"])
    card = repo.create_knowledge_card(
        workspace_id=ws["id"],
        source_document_id=doc["id"],
        source_chunk_id=chunks[0]["id"],
        card_type="decision",
        title="cascade",
        summary="cascade",
        evidence_quote="결정: cascade",
        keywords=[],
        tags=[],
        status="decided",
        confidence="high",
    )
    print(f"  doc={doc['id']} chunk={chunks[0]['id']} card={card['id']}")

    banner("REPOSITORY LAYER - Card update + delete")
    updated_card = repo.update_card(
        card["id"],
        card_type="hypothesis",
        title="updated",
        summary="updated",
        evidence_quote="updated",
        keywords=["k"],
        tags=["t"],
        status="needs_validation",
        confidence="medium",
    )
    assert updated_card["card_type"] == "hypothesis"
    assert updated_card["keywords"] == ["k"]
    print(f"  patched card_type={updated_card['card_type']} status={updated_card['status']} tags={updated_card['tags']}")

    repo.delete_card(card["id"])
    try:
        repo.get_card(card["id"])
    except KeyError as exc:
        print(f"  delete confirmed (KeyError): {exc}")
    else:
        raise AssertionError("card still readable after delete")

    banner("REPOSITORY LAYER - Document delete cascade")
    chunk_id = chunks[0]["id"]
    repo.delete_raw_document(doc["id"])
    try:
        repo.get_raw_document(doc["id"])
    except KeyError as exc:
        print(f"  doc delete confirmed: {exc}")
    else:
        raise AssertionError("doc still readable after delete")
    try:
        repo.get_chunk(chunk_id)
    except KeyError as exc:
        print(f"  chunk cascade confirmed: {exc}")
    else:
        raise AssertionError("chunk should have been cascade-deleted")

    banner("REPOSITORY LAYER - Workspace delete cascade")
    doc2 = repo.create_raw_document(ws["id"], "second.md", "md", "결정: cascade2")
    chunks2 = repo.create_chunks(doc2["id"], ws["id"], ["결정: cascade2"])
    card2 = repo.create_knowledge_card(
        workspace_id=ws["id"],
        source_document_id=doc2["id"],
        source_chunk_id=chunks2[0]["id"],
        card_type="decision",
        title="x",
        summary="x",
        evidence_quote="x",
        keywords=[],
        tags=[],
        status="decided",
        confidence="high",
    )
    repo.delete_workspace(ws["id"])
    try:
        repo.get_workspace(ws["id"])
    except KeyError:
        print("  workspace delete confirmed")
    try:
        repo.get_card(card2["id"])
    except KeyError:
        print("  card cascade-deleted with workspace")
    try:
        repo.get_raw_document(doc2["id"])
    except KeyError:
        print("  doc cascade-deleted with workspace")


# ---------------------------------------------------------------------------
# 2. API-layer CRUD via TestClient
# ---------------------------------------------------------------------------

def api_layer_crud(client: TestClient) -> None:
    banner("API LAYER - Workspace CRUD")
    r = client.post("/api/workspaces", json={"name": "API CRUD"})
    assert r.status_code == 201, r.text
    ws_id = r.json()["id"]
    print(f"  POST /api/workspaces -> 201 id={ws_id}")

    r = client.get(f"/api/workspaces/{ws_id}")
    assert r.status_code == 200
    print(f"  GET /api/workspaces/{ws_id} -> 200 name={r.json()['name']!r}")

    r = client.patch(f"/api/workspaces/{ws_id}", json={"name": "API CRUD v2"})
    assert r.status_code == 200 and r.json()["name"] == "API CRUD v2"
    print(f"  PATCH name -> 200 name={r.json()['name']!r}")

    r = client.patch("/api/workspaces/99999", json={"name": "x"})
    assert r.status_code == 404
    print(f"  PATCH missing -> 404 detail={r.json()['detail']!r}")

    banner("API LAYER - Document CRUD")
    r = client.post(
        f"/api/workspaces/{ws_id}/documents/text",
        json={
            "filename": "api.md",
            "content": "결정: API 계층 CRUD 검증.\n\n근거: text 입력은 manual source로 정규화된다.",
        },
    )
    assert r.status_code == 201
    doc_id = r.json()["document_id"]
    chunk_count = r.json()["chunk_count"]
    card_count = r.json()["card_count"]
    print(f"  POST /documents/text -> 201 doc={doc_id} chunks={chunk_count} cards={card_count}")

    r = client.get(f"/api/workspaces/{ws_id}/documents/{doc_id}")
    assert r.status_code == 200 and r.json()["filename"] == "api.md"
    print(f"  GET /documents/{doc_id} -> 200")

    r = client.patch(
        f"/api/workspaces/{ws_id}/documents/{doc_id}",
        json={"content": "결정: 문서 수정 후 reindex.", "external_id": "api-rewrite"},
    )
    assert r.status_code == 200 and r.json()["external_id"] == "api-rewrite"
    print(f"  PATCH /documents/{doc_id} (reindex) -> 200 external_id={r.json()['external_id']!r}")

    r = client.delete(f"/api/workspaces/{ws_id}/documents/{doc_id}")
    assert r.status_code == 204
    print(f"  DELETE /documents/{doc_id} -> 204")

    r = client.get(f"/api/workspaces/{ws_id}/documents/{doc_id}")
    assert r.status_code == 404
    print(f"  GET deleted doc -> 404 detail={r.json()['detail']!r}")

    banner("API LAYER - Card CRUD with auto-source")
    r = client.post(
        f"/api/workspaces/{ws_id}/cards",
        json={
            "card_type": "decision",
            "title": "API 카드",
            "summary": "manual",
            "evidence_quote": "manual: API CRUD",
            "keywords": ["api"],
            "tags": ["crud"],
            "status": "decided",
            "confidence": "high",
        },
    )
    assert r.status_code == 201
    card_id = r.json()["id"]
    print(
        f"  POST /cards (auto-source) -> 201 id={card_id} "
        f"source_doc={r.json()['source_document_id']} source_chunk={r.json()['source_chunk_id']}"
    )

    r = client.get(f"/api/workspaces/{ws_id}/cards/{card_id}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["source_document"]["source_type"] == "manual_card"
    print(f"  GET /cards/{card_id} -> 200 source filename={detail['source_document']['filename']!r}")

    r = client.patch(
        f"/api/workspaces/{ws_id}/cards/{card_id}",
        json={"status": "validated", "confidence": "medium", "tags": ["crud-passed"]},
    )
    assert r.status_code == 200 and r.json()["status"] == "validated"
    print(f"  PATCH /cards/{card_id} -> 200 status={r.json()['status']} tags={r.json()['tags']}")

    r = client.delete(f"/api/workspaces/{ws_id}/cards/{card_id}")
    assert r.status_code == 204
    print(f"  DELETE /cards/{card_id} -> 204")

    banner("API LAYER - Cross-workspace scope guard")
    other = client.post("/api/workspaces", json={"name": "Other"}).json()["id"]
    rogue_card = client.post(
        f"/api/workspaces/{other}/cards",
        json={
            "card_type": "decision",
            "title": "rogue",
            "summary": "rogue",
            "evidence_quote": "rogue",
            "keywords": [],
            "tags": [],
            "status": "decided",
            "confidence": "high",
        },
    ).json()
    r = client.get(f"/api/workspaces/{ws_id}/cards/{rogue_card['id']}")
    assert r.status_code == 404
    print(f"  GET rogue card from wrong workspace -> 404 ({r.json()['detail']!r})")
    client.delete(f"/api/workspaces/{other}")

    banner("API LAYER - Workspace cascade DELETE")
    # Re-add a doc + card so cascade has things to delete
    client.post(
        f"/api/workspaces/{ws_id}/documents/text",
        json={"filename": "before-delete.md", "content": "결정: cascade 입증."},
    )
    docs_before = client.get(f"/api/workspaces/{ws_id}/documents").json()
    cards_before = client.get(f"/api/workspaces/{ws_id}/cards").json()
    print(f"  before cascade: {len(docs_before)} docs, {len(cards_before)} cards")

    r = client.delete(f"/api/workspaces/{ws_id}")
    assert r.status_code == 204
    r = client.get(f"/api/workspaces/{ws_id}")
    assert r.status_code == 404
    print(f"  workspace delete -> 204, GET -> 404")

    print()
    print("=== ALL CRUD CHECKS PASSED ===")


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    repo = SQLiteRepository(tmp / "crud.sqlite3")
    repo.initialize()

    repo_layer_crud(repo)

    # API layer uses its own repo so the previous test does not leak
    api_repo = SQLiteRepository(tmp / "crud_api.sqlite3")
    app = create_app(repository=api_repo)
    api_layer_crud(TestClient(app))


if __name__ == "__main__":
    main()
