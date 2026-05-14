"""Edge-case + error-handling verification for the FastAPI surface.

Hits the live backend at http://127.0.0.1:8000 with intentionally bad
inputs and asserts the right HTTP status + diagnostic body comes back.

Run with the backend already up.
"""

from __future__ import annotations

from io import BytesIO

import httpx
from pypdf import PdfWriter

BASE = "http://127.0.0.1:8000"


def banner(label: str) -> None:
    print()
    print(f"=== {label} ===")


def main() -> None:
    # Create a clean disposable workspace
    ws = httpx.post(f"{BASE}/api/workspaces", json={"name": "EdgeCases"}, timeout=30).json()["id"]
    print(f"workspace_id={ws}")

    try:
        # --- 1. malformed JSON body ---
        banner("malformed JSON to /qa")
        r = httpx.post(
            f"{BASE}/api/workspaces/{ws}/qa",
            content=b"{not even json",
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        print(f"  HTTP {r.status_code} body={r.text[:120]}")
        assert r.status_code == 422  # FastAPI uses 422 for JSON parse errors

        # --- 2. empty body for POST that requires payload ---
        banner("empty JSON to POST /workspaces")
        r = httpx.post(f"{BASE}/api/workspaces", content=b"{}", headers={"Content-Type": "application/json"}, timeout=10)
        print(f"  HTTP {r.status_code} body={r.text[:200]}")
        assert r.status_code == 422  # Pydantic validation error

        # --- 3. card without required field ---
        banner("card POST missing 'card_type'")
        r = httpx.post(
            f"{BASE}/api/workspaces/{ws}/cards",
            json={"title": "x", "summary": "x", "evidence_quote": "x"},
            timeout=10,
        )
        print(f"  HTTP {r.status_code} body={r.text[:200]}")
        assert r.status_code == 422

        # --- 4. card with invalid card_type literal ---
        banner("card POST with invalid card_type")
        r = httpx.post(
            f"{BASE}/api/workspaces/{ws}/cards",
            json={
                "card_type": "INVALID_TYPE",
                "title": "x",
                "summary": "x",
                "evidence_quote": "x",
                "keywords": [],
                "tags": [],
                "status": "proposed",
                "confidence": "medium",
            },
            timeout=10,
        )
        print(f"  HTTP {r.status_code} body={r.text[:200]}")
        assert r.status_code == 422

        # --- 5. workspace scope: card from another workspace ---
        banner("card cross-workspace 404")
        ws_other = httpx.post(f"{BASE}/api/workspaces", json={"name": "Other"}, timeout=10).json()["id"]
        card = httpx.post(
            f"{BASE}/api/workspaces/{ws_other}/cards",
            json={
                "card_type": "decision",
                "title": "scope-test",
                "summary": "scope-test",
                "evidence_quote": "scope-test",
                "keywords": [],
                "tags": [],
                "status": "decided",
                "confidence": "high",
            },
            timeout=10,
        ).json()
        r = httpx.get(f"{BASE}/api/workspaces/{ws}/cards/{card['id']}", timeout=10)
        print(f"  HTTP {r.status_code} body={r.text[:120]} (card belongs to ws {ws_other}, asked ws {ws})")
        assert r.status_code == 404
        httpx.delete(f"{BASE}/api/workspaces/{ws_other}", timeout=10)

        # --- 6. ingestion of unsupported file type ---
        banner("upload unsupported .mp3")
        r = httpx.post(
            f"{BASE}/api/workspaces/{ws}/documents/upload",
            files={"file": ("audio.mp3", b"not audio bytes", "audio/mpeg")},
            data={"source_type": "manual"},
            timeout=10,
        )
        print(f"  HTTP {r.status_code} body={r.text[:200]}")
        assert r.status_code == 400

        # --- 7. scanned/empty PDF ---
        banner("upload empty PDF (no text)")
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        buffer = BytesIO()
        writer.write(buffer)
        r = httpx.post(
            f"{BASE}/api/workspaces/{ws}/documents/upload",
            files={"file": ("blank.pdf", buffer.getvalue(), "application/pdf")},
            data={"source_type": "pdf"},
            timeout=30,
        )
        print(f"  HTTP {r.status_code} body={r.text[:200]}")
        assert r.status_code == 400

        # --- 8. search with no query (missing required q) ---
        banner("search without ?q=")
        r = httpx.get(f"{BASE}/api/workspaces/{ws}/search", timeout=10)
        print(f"  HTTP {r.status_code} body={r.text[:120]}")
        assert r.status_code == 422

        # --- 9. search with empty q ---
        banner("search with ?q= (empty)")
        r = httpx.get(f"{BASE}/api/workspaces/{ws}/search?q=", timeout=10)
        print(f"  HTTP {r.status_code} body={r.text[:120]}")
        assert r.status_code == 422  # Query(min_length=1)

        # --- 10. search empty workspace ---
        banner("search on empty workspace returns empty")
        r = httpx.get(f"{BASE}/api/workspaces/{ws}/search?q=anything", timeout=10)
        print(f"  HTTP {r.status_code} cards={len(r.json()['cards'])} chunks={len(r.json()['chunks'])}")
        assert r.status_code == 200

        # --- 11. QA on empty workspace (insufficient context) ---
        banner("QA on empty workspace")
        r = httpx.post(f"{BASE}/api/workspaces/{ws}/qa", json={"question": "데이터 없음"}, timeout=120)
        body = r.json()
        print(f"  HTTP {r.status_code} confidence={body['confidence']} cards={len(body['evidence_cards'])}")
        print(f"  missing_evidence: {body['missing_evidence'][:1]}")
        print(f"  answer: {body['answer'][:100]}")
        assert r.status_code == 200
        assert body["confidence"] in {"low", "medium", "high"}
        assert body["evidence_cards"] == []

        # --- 12. moderately long content ingestion (within Upstage budget) ---
        banner("ingest 2K-char text with multiple chunks")
        long_text = "결정: 큰 텍스트도 정상 처리한다.\n\n" + (
            "근거: chunk 분할 후 LLM 추출이 동작해야 한다. " * 30
        ) + "\n\n리스크: 호출 비용은 chunk 수에 비례한다."
        r = httpx.post(
            f"{BASE}/api/workspaces/{ws}/documents/text",
            json={"filename": "long.md", "content": long_text},
            timeout=300,
        )
        result = r.json()
        print(f"  HTTP {r.status_code} chunks={result['chunk_count']} cards={result['card_count']} doc_id={result['document_id']}")
        assert r.status_code == 201

        # --- 13. PATCH workspace with empty body ---
        banner("PATCH workspace {} (no fields)")
        r = httpx.patch(f"{BASE}/api/workspaces/{ws}", json={}, timeout=10)
        print(f"  HTTP {r.status_code} body={r.text[:120]}")
        assert r.status_code == 200  # all-optional patch should accept

        # --- 14. PATCH card with empty body ---
        banner("PATCH card {} (no fields)")
        cards = httpx.get(f"{BASE}/api/workspaces/{ws}/cards", timeout=10).json()
        if cards:
            r = httpx.patch(f"{BASE}/api/workspaces/{ws}/cards/{cards[0]['id']}", json={}, timeout=10)
            print(f"  HTTP {r.status_code} body={r.text[:120]}")
            assert r.status_code == 200

        # --- 15. delete non-existent card ---
        banner("DELETE non-existent card")
        r = httpx.delete(f"{BASE}/api/workspaces/{ws}/cards/9999999", timeout=10)
        print(f"  HTTP {r.status_code} body={r.text[:120]}")
        assert r.status_code == 404

        # --- 16. card paths with depth too high ---
        banner("card paths depth=99 (clamps to max)")
        if cards:
            r = httpx.get(f"{BASE}/api/workspaces/{ws}/cards/{cards[0]['id']}/paths?depth=99", timeout=10)
            body = r.json()
            print(f"  HTTP {r.status_code} max_depth={body['max_depth']} (expected 3, clamp)")
            assert r.status_code == 200
            assert body["max_depth"] == 3

        print()
        print("=== ALL EDGE-CASE CHECKS PASSED ===")
    finally:
        httpx.delete(f"{BASE}/api/workspaces/{ws}", timeout=10)


if __name__ == "__main__":
    main()
