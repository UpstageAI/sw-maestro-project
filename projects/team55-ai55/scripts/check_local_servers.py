from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


FE_BASE_URL = os.getenv("FE_BASE_URL", "http://127.0.0.1:5173/").rstrip("/") + "/"
BE_BASE_URL = os.getenv("BE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ALLOWED_ORIGIN = os.getenv("CHECK_ALLOWED_ORIGIN", "http://127.0.0.1:5173")
REJECTED_ORIGIN = os.getenv("CHECK_REJECTED_ORIGIN", "http://127.0.0.1:5174")


def fetch_json(url: str) -> tuple[int, dict]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=3) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=3) as response:
        return response.status, response.read(262144).decode("utf-8", errors="replace")


def preflight(origin: str) -> tuple[int, str | None, str]:
    request = urllib.request.Request(
        f"{BE_BASE_URL}/v1/projects",
        method="OPTIONS",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, response.headers.get("access-control-allow-origin"), response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("access-control-allow-origin"), error.read().decode()


def main() -> int:
    result = {"ok": True, "fe_url": FE_BASE_URL, "be_url": BE_BASE_URL, "checks": {}}
    try:
        be_status, health = fetch_json(f"{BE_BASE_URL}/v1/health")
        result["checks"]["backend_health"] = {
            "ok": be_status == 200 and health.get("status") == "ok",
            "status": be_status,
            "body_status": health.get("status"),
            "upstage_configured": health.get("upstage_api", {}).get("configured"),
        }
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
        result["checks"]["backend_health"] = {"ok": False, "error": str(error)}

    try:
        openapi_status, openapi = fetch_json(f"{BE_BASE_URL}/openapi.json")
        openapi_text = json.dumps(openapi, ensure_ascii=False)
        result["checks"]["backend_openapi_contract"] = {
            "ok": openapi_status == 200
            and "/v1/projects/{project_id}/risk:simulate" in openapi.get("paths", {})
            and "score_action_coherence" in openapi_text,
            "status": openapi_status,
            "has_risk_simulate": "/v1/projects/{project_id}/risk:simulate" in openapi.get("paths", {}),
            "has_score_action_coherence": "score_action_coherence" in openapi_text,
        }
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
        result["checks"]["backend_openapi_contract"] = {"ok": False, "error": str(error)}

    try:
        fe_status, html = fetch_text(FE_BASE_URL)
        result["checks"]["frontend_html"] = {
            "ok": fe_status == 200 and 'id="root"' in html and "/src/main.tsx" in html,
            "status": fe_status,
            "contains_root": 'id="root"' in html,
            "contains_vite_entry": "/src/main.tsx" in html,
        }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        result["checks"]["frontend_html"] = {"ok": False, "error": str(error)}

    try:
        module_status, api_client_module = fetch_text(f"{FE_BASE_URL}src/app/apiClient.ts")
        result["checks"]["frontend_api_client_module"] = {
            "ok": module_status == 200
            and "VITE_API_BASE_URL" in api_client_module
            and "http://127.0.0.1:8000" in api_client_module
            and "http://127.0.0.1:8002" not in api_client_module
            and "http://127.0.0.1:8013" not in api_client_module
            and "http://127.0.0.1:8014" not in api_client_module
            and "http://127.0.0.1:8015" not in api_client_module,
            "status": module_status,
            "has_vite_api_base": "VITE_API_BASE_URL" in api_client_module,
            "has_current_backend": "http://127.0.0.1:8000" in api_client_module,
            "has_stale_8002": "http://127.0.0.1:8002" in api_client_module,
            "has_stale_8013": "http://127.0.0.1:8013" in api_client_module,
            "has_stale_8014": "http://127.0.0.1:8014" in api_client_module,
            "has_stale_8015": "http://127.0.0.1:8015" in api_client_module,
        }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        result["checks"]["frontend_api_client_module"] = {"ok": False, "error": str(error)}

    try:
        dashboard_status, dashboard_module = fetch_text(f"{FE_BASE_URL}src/app/pages/Dashboard.tsx")
        result["checks"]["frontend_dashboard_module"] = {
            "ok": dashboard_status == 200
            and "updateCalendarEventAndReanalyze" not in dashboard_module
            and "moveCalendarEventAndReanalyze" in dashboard_module
            and "onMoveEvent" in dashboard_module,
            "status": dashboard_status,
            "has_stale_calendar_update": "updateCalendarEventAndReanalyze" in dashboard_module,
            "has_move_reanalyze": "moveCalendarEventAndReanalyze" in dashboard_module,
            "has_on_move_event": "onMoveEvent" in dashboard_module,
        }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        result["checks"]["frontend_dashboard_module"] = {"ok": False, "error": str(error)}

    try:
        allowed_status, allowed_header, _ = preflight(ALLOWED_ORIGIN)
        rejected_status, rejected_header, rejected_body = preflight(REJECTED_ORIGIN)
        result["checks"]["cors_preflight"] = {
            "ok": allowed_status == 200
            and allowed_header == ALLOWED_ORIGIN
            and rejected_status == 400
            and rejected_header is None,
            "allowed_origin": ALLOWED_ORIGIN,
            "allowed_status": allowed_status,
            "allowed_header": allowed_header,
            "rejected_origin": REJECTED_ORIGIN,
            "rejected_status": rejected_status,
            "rejected_header": rejected_header,
            "rejected_body": rejected_body,
        }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        result["checks"]["cors_preflight"] = {"ok": False, "error": str(error)}

    result["ok"] = all(check["ok"] for check in result["checks"].values())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
