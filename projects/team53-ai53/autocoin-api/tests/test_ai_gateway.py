from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.services import ai_gateway_service


def _mock_client(response_json: dict):
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_json
    mock_resp.raise_for_status = MagicMock()
    mock_post = AsyncMock(return_value=mock_resp)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx, mock_post


@pytest.mark.asyncio
async def test_start_run_sends_correct_payload():
    ctx, mock_post = _mock_client({"lifecycle_status": "READY_FOR_BE", "run_id": "r1"})
    with patch("app.services.ai_gateway_service.httpx.AsyncClient", return_value=ctx):
        result = await ai_gateway_service.start_run("r1", {"request_id": "r1"}, {"policy_refs": []}, settings)
    assert result["lifecycle_status"] == "READY_FOR_BE"
    call_kwargs = mock_post.call_args
    assert "runs/start" in call_kwargs.args[0]
    body = call_kwargs.kwargs["json"]
    assert body["run_id"] == "r1"
    assert "request_context" in body
    assert "policy_context" in body


@pytest.mark.asyncio
async def test_resume_run_sends_correct_payload():
    ctx, mock_post = _mock_client({"lifecycle_status": "HOLD", "run_id": "r1"})
    with patch("app.services.ai_gateway_service.httpx.AsyncClient", return_value=ctx):
        result = await ai_gateway_service.resume_run("r1", "USER_APPROVED_ORDER", {"approval": {"approved": True}}, settings)
    assert result["lifecycle_status"] == "HOLD"
    body = mock_post.call_args.kwargs["json"]
    assert body["run_id"] == "r1"
    assert body["resume_reason"] == "USER_APPROVED_ORDER"
    assert body["patch_fields"]["approval"]["approved"] is True


@pytest.mark.asyncio
async def test_send_completion_with_execution_result():
    ctx, mock_post = _mock_client({"lifecycle_status": "REPORT_READY", "run_id": "r1"})
    with patch("app.services.ai_gateway_service.httpx.AsyncClient", return_value=ctx):
        result = await ai_gateway_service.send_completion(
            "r1", {"execution_result": {"orderId": 123, "status": "NEW"}}, settings
        )
    assert result["lifecycle_status"] == "REPORT_READY"
    body = mock_post.call_args.kwargs["json"]
    assert "execution_result" in body["completion_payload"]


@pytest.mark.asyncio
async def test_send_completion_with_be_rejection():
    ctx, mock_post = _mock_client({"lifecycle_status": "BE_REJECTED", "run_id": "r1"})
    with patch("app.services.ai_gateway_service.httpx.AsyncClient", return_value=ctx):
        result = await ai_gateway_service.send_completion(
            "r1", {"be_rejection_evidence": {"reason_codes": ["MIN_NOTIONAL_NOT_MET"]}}, settings
        )
    assert result["lifecycle_status"] == "BE_REJECTED"
    body = mock_post.call_args.kwargs["json"]
    assert "be_rejection_evidence" in body["completion_payload"]
