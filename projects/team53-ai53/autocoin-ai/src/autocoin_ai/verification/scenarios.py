"""Deterministic QA scenarios derived from docs/TEST_AND_DEMO.md and docs/qa.md."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def allowed_request(run_id: str = "airun_verify_allowed") -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "request_context": {
            "request_id": "req_verify_allowed",
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": "2026-05-07T10:00:00+09:00",
            "user_input": {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "MARKET",
                "quoteOrderQty": "50",
            },
        },
        "policy_context": {"policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]},
    }


def request_with_user_input(run_id: str, **updates: Any) -> Dict[str, Any]:
    payload = deepcopy(allowed_request(run_id))
    payload["request_context"]["user_input"].update(updates)
    return payload


def execution_result() -> Dict[str, Any]:
    return {"execution_result": {"status": "FILLED", "orderId": 123456789, "clientOrderId": "demo-order-001"}}


def be_rejection_evidence() -> Dict[str, Any]:
    return {
        "be_rejection_evidence": {
            "reason_codes": ["MIN_NOTIONAL_NOT_MET"],
            "notes": "Deterministic revalidation blocked the order before submit.",
        }
    }


def schema_mismatch_request() -> Dict[str, Any]:
    payload = allowed_request("airun_verify_failed")
    del payload["request_context"]["user_input"]["symbol"]
    return payload
