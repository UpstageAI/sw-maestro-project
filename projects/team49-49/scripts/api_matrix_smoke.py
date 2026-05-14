"""One-shot live API matrix verification against http://127.0.0.1:8770.

Run with the backend already up. Hits every operation registered in the
OpenAPI schema (plus a few negative paths) and prints a pass/fail table.
"""

from __future__ import annotations

import httpx

BASE = "http://127.0.0.1:8770"


def main() -> None:
    results: list[tuple[str, str, int, int, bool, int]] = []

    def check(method: str, path: str, expected_status: int, **kwargs) -> httpx.Response:
        response = httpx.request(method, BASE + path, timeout=60, **kwargs)
        ok = response.status_code == expected_status
        results.append((method, path, expected_status, response.status_code, ok, len(response.content)))
        return response

    def upload(path: str, files: dict, data: dict, expected_status: int) -> httpx.Response:
        response = httpx.post(BASE + path, files=files, data=data, timeout=60)
        results.append(("POST", path, expected_status, response.status_code, response.status_code == expected_status, len(response.content)))
        return response

    # ===== infrastructure =====
    check("GET", "/health", 200)
    check("GET", "/", 200)
    check("GET", "/openapi.json", 200)
    check("GET", "/docs", 200)
    check("GET", "/redoc", 200)
    check("GET", "/favicon.ico", 200)
    check("GET", "/api/workflows", 200)

    # ===== workspace CRUD =====
    r = check("POST", "/api/workspaces", 201, json={"name": "API Matrix", "description": "sweep"})
    ws = r.json()["id"]
    check("GET", "/api/workspaces", 200)
    check("GET", f"/api/workspaces/{ws}", 200)
    check("PATCH", f"/api/workspaces/{ws}", 200, json={"description": "patched"})
    check("GET", "/api/workspaces/999999", 404)

    # ===== document text ingestion =====
    r = check(
        "POST",
        f"/api/workspaces/{ws}/documents/text",
        201,
        json={
            "filename": "inline.md",
            "content": "결정: API 매트릭스 검증.\n\n근거: 모든 endpoint를 한 번씩 두드린다.",
        },
    )
    doc_id = r.json()["document_id"]
    check("GET", f"/api/workspaces/{ws}/documents", 200)
    check("GET", f"/api/workspaces/{ws}/documents/{doc_id}", 200)

    # ===== document source ingestion =====
    r = check(
        "POST",
        f"/api/workspaces/{ws}/documents/source",
        201,
        json={
            "source_type": "manual",
            "source_url": "",
            "external_id": "mx-1",
            "title": "src.md",
            "content": "리스크: API 검증 자동화도 회귀 가능성이 있다.",
        },
    )

    # ===== document upload =====
    upload_text = "결정: 업로드 경로도 검증한다.\n\n근거: txt 파일은 utf-8 디코드.".encode("utf-8")
    r = upload(
        f"/api/workspaces/{ws}/documents/upload",
        files={"file": ("uploaded.txt", upload_text, "text/plain")},
        data={"source_type": "txt", "source_url": "local://api-matrix", "external_id": "mx-up"},
        expected_status=201,
    )
    upload_doc_id = r.json()["document_id"]

    # ===== document PATCH + DELETE =====
    check(
        "PATCH",
        f"/api/workspaces/{ws}/documents/{doc_id}",
        200,
        json={"content": "근거: PATCH 후 reindex 검증한다."},
    )
    check("DELETE", f"/api/workspaces/{ws}/documents/{upload_doc_id}", 204)

    # ===== cards =====
    check("GET", f"/api/workspaces/{ws}/cards", 200)
    check("GET", f"/api/workspaces/{ws}/cards?card_type=decision", 200)
    r = check(
        "POST",
        f"/api/workspaces/{ws}/cards",
        201,
        json={
            "card_type": "hypothesis",
            "title": "API matrix 가설",
            "summary": "manual card 검증",
            "evidence_quote": "manual: API matrix 검증",
            "keywords": ["api", "matrix"],
            "tags": [],
            "status": "needs_validation",
            "confidence": "medium",
        },
    )
    card_id = r.json()["id"]
    check("GET", f"/api/workspaces/{ws}/cards/{card_id}", 200)
    check("PATCH", f"/api/workspaces/{ws}/cards/{card_id}", 200, json={"status": "validated", "tags": ["mx"]})
    check("GET", f"/api/workspaces/{ws}/cards/{card_id}/relations", 200)
    check("GET", f"/api/workspaces/{ws}/cards/{card_id}/paths?depth=2", 200)
    check("DELETE", f"/api/workspaces/{ws}/cards/{card_id}", 204)

    # ===== search + qa + reviews =====
    check("GET", f"/api/workspaces/{ws}/search?q=API", 200)
    check("GET", f"/api/workspaces/{ws}/search?q=결정&card_type=decision&source_type=manual&top_k=3", 200)
    check("POST", f"/api/workspaces/{ws}/search/llm", 200, json={"query": "API matrix 검증의 핵심은?"})
    check("POST", f"/api/workspaces/{ws}/qa", 200, json={"question": "API matrix 검증의 핵심은?"})
    check("GET", f"/api/workspaces/{ws}/qa/history", 200)
    check("POST", f"/api/workspaces/{ws}/reviews/run", 200)

    # ===== graph =====
    check("GET", f"/api/workspaces/{ws}/graph", 200)

    # ===== cascade DELETE last =====
    check("DELETE", f"/api/workspaces/{ws}", 204)
    check("GET", f"/api/workspaces/{ws}", 404)

    # ===== error paths =====
    check("GET", "/api/workspaces/999999/cards", 200)
    check(
        "POST",
        "/api/workspaces/999999/cards",
        404,
        json={
            "card_type": "idea",
            "title": "x",
            "summary": "x",
            "evidence_quote": "x",
        },
    )
    check("PATCH", "/api/workspaces/999999", 404, json={"name": "nope"})
    check("DELETE", "/api/workspaces/999999", 404)

    print(f"=== {len(results)} operations executed ===")
    for method, path, expected, got, ok, size in results:
        flag = "OK " if ok else "BAD"
        print(f"  [{flag}] {method:6s} {path:65s} expect={expected} got={got} bytes={size}")
    passed = sum(1 for r in results if r[4])
    failed = len(results) - passed
    print()
    print(f"PASS={passed}/{len(results)}  FAIL={failed}")


if __name__ == "__main__":
    main()
