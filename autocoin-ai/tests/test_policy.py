"""Tests for updated policy_node (Phase 3a-2)."""

from __future__ import annotations

from autocoin_ai.constants import LIFECYCLE_FAILED, PASS_ACTION
from autocoin_ai.models import ensure_state_shape
from autocoin_ai.nodes.policy import policy_node

BASE_REQUEST_CONTEXT = {
    "request_id": "req_test_policy",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T10:00:00+09:00",
    "user_input": {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quoteOrderQty": "100",
    },
}

POLICY_CONTEXT = {"policy_refs": ["policy.spot_testnet_only"]}


def _make_state(extra: dict | None = None) -> dict:
    base = {
        "run_id": "test_run",
        "request_context": BASE_REQUEST_CONTEXT,
        "policy_context": POLICY_CONTEXT,
    }
    if extra:
        base.update(extra)
    return ensure_state_shape(base)


def test_policy_grounding():
    state = _make_state()
    result = policy_node(state)
    assert result["lifecycle_status"] != LIFECYCLE_FAILED
    assert result["decision_trace"]["policy"]["final_action"] == PASS_ACTION
    assert "POLICY_GROUNDED" in result["decision_trace"]["policy"]["reason_codes"]
    assert "persona" in result["policy_context"]
    assert "persona_bounds" in result["policy_context"]
    assert isinstance(result["trader_principles"], list)
    assert len(result["trader_principles"]) > 0


def test_policy_passes_failed():
    state = _make_state({"lifecycle_status": LIFECYCLE_FAILED})
    result = policy_node(state)
    assert result["lifecycle_status"] == LIFECYCLE_FAILED
    assert result["decision_trace"]["policy"]["final_action"] == ""
