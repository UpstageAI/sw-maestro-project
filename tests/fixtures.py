from __future__ import annotations

from copy import deepcopy

from typing import Any


def allowed_request() -> dict[str, Any]:
    return {
        "run_id": "airun_test_001",
        "request_context": {
            "request_id": "req_test_001",
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


def request_with_user_input(**updates: Any) -> dict[str, Any]:
    payload = deepcopy(allowed_request())
    payload["request_context"]["user_input"].update(updates)
    return payload


def execution_result() -> dict[str, Any]:
    return {"execution_result": {"status": "FILLED", "orderId": 123456789, "clientOrderId": "demo-order-001"}}


def be_rejection_evidence() -> dict[str, Any]:
    return {
        "be_rejection_evidence": {
            "reason_codes": ["MIN_NOTIONAL_NOT_MET"],
            "notes": "Deterministic revalidation blocked the order before submit.",
        }
    }
