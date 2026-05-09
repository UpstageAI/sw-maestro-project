from __future__ import annotations

from fastapi.testclient import TestClient

from autocoin_ai.constants import LIFECYCLE_HOLD, LIFECYCLE_READY_FOR_BE, LIFECYCLE_REPORT_READY
from autocoin_ai.http_api import app
from tests.fixtures import allowed_request, execution_result, request_with_user_input


def test_start_endpoint_returns_canonical_agent_state():
    with TestClient(app) as client:
        response = client.post("/runs/start", json=allowed_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "airun_test_001"
    assert payload["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert set(("policy", "risk", "evaluator", "execution", "run_summary")).issubset(payload["decision_trace"].keys())


def test_resume_endpoint_resumes_hold_run():
    with TestClient(app) as client:
        initial = client.post("/runs/start", json=request_with_user_input(market_snapshot_fresh=False))
        initial_payload = initial.json()
        response = client.post(
            "/runs/resume",
            json={
                "run_id": "airun_test_001",
                "resume_reason": "MARKET_DATA_SUPPLIED",
                "patch_fields": {"supplemental_user_input": {"market_snapshot_fresh": True}},
            },
        )

    assert initial.status_code == 200
    assert initial.json()["lifecycle_status"] == LIFECYCLE_HOLD
    assert response.status_code == 200
    payload = response.json()
    assert payload["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert payload["request_context"] == initial_payload["request_context"]
    assert payload["resume_history"][0]["resume_reason"] == "MARKET_DATA_SUPPLIED"
    assert payload["decision_trace_history"][0]["decision_trace"]["risk"] == initial_payload["decision_trace"]["risk"]


def test_complete_endpoint_accepts_execution_result():
    with TestClient(app) as client:
        start = client.post("/runs/start", json=allowed_request())
        response = client.post(
            "/runs/complete",
            json={"run_id": "airun_test_001", "completion_payload": execution_result()},
        )

    assert start.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["lifecycle_status"] == LIFECYCLE_REPORT_READY
    assert payload["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_REPORT_READY


def test_start_endpoint_rejects_missing_run_id():
    payload = allowed_request()
    del payload["run_id"]

    with TestClient(app) as client:
        response = client.post("/runs/start", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "run_id is required"}


def test_resume_endpoint_returns_not_found_for_unknown_run():
    with TestClient(app) as client:
        response = client.post(
            "/runs/resume",
            json={
                "run_id": "airun_missing",
                "resume_reason": "MARKET_DATA_SUPPLIED",
                "patch_fields": {"supplemental_user_input": {"market_snapshot_fresh": True}},
            },
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "unknown run_id: airun_missing"}


def test_resume_endpoint_rejects_non_hold_run():
    with TestClient(app) as client:
        start = client.post("/runs/start", json=allowed_request())
        response = client.post(
            "/runs/resume",
            json={
                "run_id": "airun_test_001",
                "resume_reason": "MARKET_DATA_SUPPLIED",
                "patch_fields": {"supplemental_user_input": {"market_snapshot_fresh": True}},
            },
        )

    assert start.status_code == 200
    assert start.json()["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert response.status_code == 400
    assert response.json() == {"detail": "only HOLD runs can be resumed"}


def test_complete_endpoint_returns_not_found_for_unknown_run():
    with TestClient(app) as client:
        response = client.post(
            "/runs/complete",
            json={"run_id": "airun_missing", "completion_payload": execution_result()},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "unknown run_id: airun_missing"}


def test_complete_endpoint_rejects_hold_run():
    with TestClient(app) as client:
        start = client.post("/runs/start", json=request_with_user_input(market_snapshot_fresh=False))
        response = client.post(
            "/runs/complete",
            json={"run_id": "airun_test_001", "completion_payload": execution_result()},
        )

    assert start.status_code == 200
    assert start.json()["lifecycle_status"] == LIFECYCLE_HOLD
    assert response.status_code == 400
    assert response.json() == {"detail": "only READY_FOR_BE runs can be completed"}


def test_complete_endpoint_rejects_failed_run():
    payload = allowed_request()
    del payload["request_context"]["user_input"]["symbol"]

    with TestClient(app) as client:
        start = client.post("/runs/start", json=payload)
        response = client.post(
            "/runs/complete",
            json={"run_id": "airun_test_001", "completion_payload": execution_result()},
        )

    assert start.status_code == 200
    assert start.json()["lifecycle_status"] == "FAILED"
    assert response.status_code == 400
    assert response.json() == {"detail": "only READY_FOR_BE runs can be completed"}
