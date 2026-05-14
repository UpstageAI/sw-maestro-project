from __future__ import annotations

from unittest.mock import patch

import autocoin_ai.tools.account_tools  # register tools
import autocoin_ai.tools.market_tools
import autocoin_ai.tools.policy_tools
from fastapi.testclient import TestClient

from autocoin_ai.constants import LIFECYCLE_HOLD, LIFECYCLE_NO_ORDER, LIFECYCLE_READY_FOR_BE, LIFECYCLE_REPORT_READY
from autocoin_ai.http_api import app, create_app
from autocoin_ai.llm import StepResult
from autocoin_ai.run_store import JsonFileRunStore
from tests.fixtures import allowed_request, execution_result, request_with_user_input


_NOOP_STEP = StepResult(is_final=True, function_calls=[], text="", candidate_content=None)
_AGENTIC_EVAL_RESP = {
    "summary": "BTC 매수 평가 완료.",
    "user_message": "매수 주문이 승인되었습니다. 주문 실행 준비가 되었습니다.",
    "reason_codes": ["RISK_GATE_PASSED"],
    "schema_warnings": [],
}


def _start_agentic_run(client: TestClient, payload: dict | None = None):
    strategy_resp = {
        "action": "BUY",
        "size_usd": "50",
        "conviction": 0.80,
        "rationale": "원칙에 맞는 진입입니다.",
        "matched_principle_titles": [],
    }
    with patch("autocoin_ai.nodes.strategy.gemini_generate", return_value=strategy_resp), patch(
        "autocoin_ai.nodes.risk_agent.gemini_step_with_tools", return_value=_NOOP_STEP
    ), patch("autocoin_ai.nodes.evaluator.gemini_generate", return_value=_AGENTIC_EVAL_RESP):
        return client.post("/runs/agentic/start", json=payload or allowed_request())


def test_start_endpoint_returns_canonical_agent_state():
    with TestClient(app) as client:
        response = client.post("/runs/start", json=allowed_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "airun_test_001"
    assert payload["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert set(("policy", "risk", "evaluator", "execution", "run_summary")).issubset(payload["decision_trace"].keys())
    assert payload["evaluator_review"]["summary"]


def test_start_endpoint_returns_evaluator_review_for_hold_run():
    with TestClient(app) as client:
        response = client.post("/runs/start", json=request_with_user_input(market_snapshot_fresh=False))

    assert response.status_code == 200
    payload = response.json()
    assert payload["lifecycle_status"] == LIFECYCLE_HOLD
    assert payload["evaluator_review"]["reason_codes"]
    assert payload["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_HOLD


def test_start_endpoint_returns_evaluator_review_for_no_order_run():
    with TestClient(app) as client:
        response = client.post("/runs/start", json=request_with_user_input(symbol="DOGEUSDT"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["lifecycle_status"] == LIFECYCLE_NO_ORDER
    assert payload["evaluator_review"]["summary"]
    assert payload["decision_trace"]["run_summary"]["final_action"] == LIFECYCLE_NO_ORDER


def test_start_agentic_endpoint_returns_canonical_agent_state():
    with TestClient(app) as client:
        response = _start_agentic_run(client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "airun_test_001"
    assert payload["trader_id"] == "wonyotti"
    assert payload["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert set(("intake", "policy", "strategy", "risk", "evaluator", "execution", "run_summary")).issubset(
        payload["decision_trace"].keys()
    )


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


def test_agentic_run_can_complete_via_existing_complete_endpoint():
    with TestClient(app) as client:
        start = _start_agentic_run(client)
        response = client.post(
            "/runs/complete",
            json={"run_id": "airun_test_001", "completion_payload": execution_result()},
        )

    assert start.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["lifecycle_status"] == LIFECYCLE_REPORT_READY
    assert payload["decision_trace"]["execution"]["final_action"] == LIFECYCLE_REPORT_READY


def test_start_endpoint_rejects_missing_run_id():
    payload = allowed_request()
    del payload["run_id"]

    with TestClient(app) as client:
        response = client.post("/runs/start", json=payload)

    assert response.status_code == 422


def test_start_endpoint_rejects_missing_policy_context_with_422():
    payload = allowed_request()
    del payload["policy_context"]

    with TestClient(app) as client:
        response = client.post("/runs/start", json=payload)

    assert response.status_code == 422


def test_start_endpoint_rejects_empty_policy_refs():
    payload = allowed_request()
    payload["policy_context"] = {"policy_refs": []}

    with TestClient(app) as client:
        response = client.post("/runs/start", json=payload)

    assert response.status_code == 200
    assert response.json()["lifecycle_status"] == "FAILED"
    assert response.json()["decision_trace"]["policy"]["reason_codes"] == ["POLICY_CONTEXT_MISSING"]


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


def test_resume_endpoint_rejects_agentic_run():
    with TestClient(app) as client:
        start = _start_agentic_run(client)
        response = client.post(
            "/runs/resume",
            json={
                "run_id": "airun_test_001",
                "resume_reason": "MARKET_DATA_SUPPLIED",
                "patch_fields": {"supplemental_user_input": {"market_snapshot_fresh": True}},
            },
        )

    assert start.status_code == 200
    assert response.status_code == 400
    assert response.json() == {"detail": "resume not supported for agentic runs in MVP"}


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


def test_resume_endpoint_accumulates_prior_resume_patches():
    with TestClient(app) as client:
        start = client.post("/runs/start", json=request_with_user_input(market_snapshot_fresh=False, requires_review=True))
        first_resume = client.post(
            "/runs/resume",
            json={
                "run_id": "airun_test_001",
                "resume_reason": "MARKET_DATA_SUPPLIED",
                "patch_fields": {"supplemental_user_input": {"market_snapshot_fresh": True}},
            },
        )
        second_resume = client.post(
            "/runs/resume",
            json={
                "run_id": "airun_test_001",
                "resume_reason": "HUMAN_REVIEW_APPROVED",
                "patch_fields": {"approval": {"approved": True}},
            },
        )

    assert start.status_code == 200
    assert first_resume.status_code == 200
    assert first_resume.json()["lifecycle_status"] == LIFECYCLE_HOLD
    assert second_resume.status_code == 200
    payload = second_resume.json()
    assert payload["lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert [entry["resume_reason"] for entry in payload["resume_history"]] == [
        "MARKET_DATA_SUPPLIED",
        "HUMAN_REVIEW_APPROVED",
    ]


def test_complete_endpoint_returns_not_found_for_unknown_run():
    with TestClient(app) as client:
        response = client.post(
            "/runs/complete",
            json={"run_id": "airun_missing", "completion_payload": execution_result()},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "unknown run_id: airun_missing"}


def test_order_checkpoint_endpoint_returns_evidence_for_standard_run():
    with TestClient(app) as client:
        start = client.post("/runs/start", json=allowed_request())
        response = client.get("/runs/airun_test_001/checkpoints/order")

    assert start.status_code == 200
    assert response.status_code == 200
    assert response.json()["final_snapshot_lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert response.json()["history_snapshot_count"] > 0


def test_order_checkpoint_endpoint_returns_evidence_for_agentic_run():
    with TestClient(app) as client:
        start = _start_agentic_run(client)
        response = client.get("/runs/airun_test_001/checkpoints/order")

    assert start.status_code == 200
    assert response.status_code == 200
    assert response.json()["final_snapshot_lifecycle_status"] == LIFECYCLE_READY_FOR_BE
    assert response.json()["history_snapshot_count"] > 0


def test_order_checkpoint_endpoint_returns_not_found_for_unknown_run():
    with TestClient(app) as client:
        response = client.get("/runs/airun_missing/checkpoints/order")

    assert response.status_code == 404
    assert response.json() == {"detail": "unknown run_id: airun_missing"}


def test_completion_checkpoint_endpoint_requires_completed_run():
    with TestClient(app) as client:
        start = client.post("/runs/start", json=allowed_request())
        response = client.get("/runs/airun_test_001/checkpoints/completion")

    assert start.status_code == 200
    assert response.status_code == 400
    assert response.json() == {"detail": "completion checkpoint not available before completion has executed"}


def test_completion_checkpoint_endpoint_returns_evidence_after_completion():
    with TestClient(app) as client:
        start = _start_agentic_run(client)
        complete = client.post(
            "/runs/complete",
            json={"run_id": "airun_test_001", "completion_payload": execution_result()},
        )
        response = client.get("/runs/airun_test_001/checkpoints/completion")

    assert start.status_code == 200
    assert complete.status_code == 200
    assert response.status_code == 200
    assert response.json()["final_snapshot_lifecycle_status"] == LIFECYCLE_REPORT_READY
    assert response.json()["history_snapshot_count"] > 0


def test_completion_checkpoint_endpoint_returns_not_found_for_unknown_run():
    with TestClient(app) as client:
        response = client.get("/runs/airun_missing/checkpoints/completion")

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


def test_resume_endpoint_survives_http_app_restart_with_file_store(tmp_path):
    store_path = tmp_path / "runs.json"

    with TestClient(create_app(JsonFileRunStore(store_path))) as first_client:
        initial = first_client.post("/runs/start", json=request_with_user_input(market_snapshot_fresh=False))

    assert initial.status_code == 200
    assert initial.json()["lifecycle_status"] == LIFECYCLE_HOLD

    with TestClient(create_app(JsonFileRunStore(store_path))) as second_client:
        response = second_client.post(
            "/runs/resume",
            json={
                "run_id": "airun_test_001",
                "resume_reason": "MARKET_DATA_SUPPLIED",
                "patch_fields": {"supplemental_user_input": {"market_snapshot_fresh": True}},
            },
        )

    assert response.status_code == 200
    assert response.json()["lifecycle_status"] == LIFECYCLE_READY_FOR_BE


def test_complete_endpoint_survives_http_app_restart_with_file_store(tmp_path):
    store_path = tmp_path / "runs.json"

    with TestClient(create_app(JsonFileRunStore(store_path))) as first_client:
        initial = first_client.post("/runs/start", json=allowed_request())

    assert initial.status_code == 200
    assert initial.json()["lifecycle_status"] == LIFECYCLE_READY_FOR_BE

    with TestClient(create_app(JsonFileRunStore(store_path))) as second_client:
        response = second_client.post(
            "/runs/complete",
            json={"run_id": "airun_test_001", "completion_payload": execution_result()},
        )

    assert response.status_code == 200
    assert response.json()["lifecycle_status"] == LIFECYCLE_REPORT_READY
