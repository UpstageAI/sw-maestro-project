from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import create_app
from app.repositories.sqlite import SQLiteRepository


def _client(tmp_path):
    repository = SQLiteRepository(tmp_path / "ich.sqlite3")
    app = create_app(repository=repository)
    return TestClient(app)


def _new_workspace(client: TestClient) -> int:
    return client.post("/api/workspaces", json={"name": "Upload Matrix"}).json()["id"]


def _upload(client, workspace_id, filename, content, source_type, mime):
    return client.post(
        f"/api/workspaces/{workspace_id}/documents/upload",
        files={"file": (filename, content, mime)},
        data={"source_type": source_type, "source_url": f"local://{filename}", "external_id": f"fixture-{source_type}"},
    )


def test_txt_upload_extracts_cards_and_preserves_metadata(tmp_path):
    client = _client(tmp_path)
    workspace_id = _new_workspace(client)

    body = (
        "결정: 텍스트 파일도 카드 추출 파이프라인을 거친다.\n\n"
        "근거: utf-8-sig 디코더가 BOM이 있어도 동작한다."
    ).encode("utf-8")
    response = _upload(client, workspace_id, "notes.txt", body, "txt", "text/plain")

    assert response.status_code == 201
    result = response.json()
    assert result["chunk_count"] >= 1
    assert result["card_count"] >= 1

    document = client.get(f"/api/workspaces/{workspace_id}/documents/{result['document_id']}").json()
    assert document["source_type"] == "txt"
    assert document["source_url"] == "local://notes.txt"
    assert document["external_id"] == "fixture-txt"
    assert "결정" in document["content"]


def test_markdown_upload_extracts_multiple_card_types(tmp_path):
    client = _client(tmp_path)
    workspace_id = _new_workspace(client)

    body = (
        "# 회의록\n\n"
        "결정: 마크다운도 같은 파이프라인을 거친다.\n\n"
        "근거: 헤더가 chunk 분리에 영향을 준다.\n\n"
        "리스크: 단일 헤더만 있는 chunk는 filter에서 제거된다."
    ).encode("utf-8")
    response = _upload(client, workspace_id, "minutes.md", body, "md", "text/markdown")

    assert response.status_code == 201
    cards = client.get(f"/api/workspaces/{workspace_id}/cards").json()
    assert {card["card_type"] for card in cards} >= {"decision", "evidence", "risk"}


def test_csv_upload_normalizes_via_pandas_and_extracts_cards(tmp_path):
    client = _client(tmp_path)
    workspace_id = _new_workspace(client)

    body = (
        "type,description\n"
        "결정,CSV는 pandas로 정규화한 뒤 그대로 chunk에 넘긴다\n"
        "근거,각 행이 chunk 후보가 되어 추출에 들어간다\n"
    ).encode("utf-8")
    response = _upload(client, workspace_id, "table.csv", body, "csv", "text/csv")

    assert response.status_code == 201
    result = response.json()
    assert result["chunk_count"] >= 1
    assert result["card_count"] >= 1

    document = client.get(f"/api/workspaces/{workspace_id}/documents/{result['document_id']}").json()
    assert document["source_type"] == "csv"
    assert document["document_type"] == "csv"
    assert "결정" in document["content"]


def test_pdf_upload_extracts_text_via_pypdf(tmp_path):
    pytest_pdf = _build_text_pdf(
        "Decision: PDF upload goes through pypdf text extraction.\n"
        "Evidence: Empty pages are skipped during extraction."
    )

    client = _client(tmp_path)
    workspace_id = _new_workspace(client)

    response = _upload(client, workspace_id, "spec.pdf", pytest_pdf, "pdf", "application/pdf")

    assert response.status_code == 201
    result = response.json()
    assert result["chunk_count"] >= 1

    document = client.get(f"/api/workspaces/{workspace_id}/documents/{result['document_id']}").json()
    assert document["source_type"] == "pdf"
    assert document["document_type"] == "pdf"
    assert "Decision" in document["content"] or "decision" in document["content"].lower()


def test_pdf_upload_rejects_empty_or_scanned_pdf(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)

    client = _client(tmp_path)
    workspace_id = _new_workspace(client)

    response = _upload(client, workspace_id, "scanned.pdf", buffer.getvalue(), "pdf", "application/pdf")

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def _build_text_pdf(text: str) -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        import pytest

        pytest.skip("reportlab not installed; cannot build text PDF fixture")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica", 12)
    y = 720
    for line in text.splitlines():
        pdf.drawString(72, y, line)
        y -= 18
    pdf.save()
    return buffer.getvalue()
