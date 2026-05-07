"""Contract validation for docs-defined payloads."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from autocoin_ai.constants import LIFECYCLE_FAILED, PASS_ACTION, TRACE_STAGES
from autocoin_ai.models import AgentState, JsonDict


REQUIRED_REQUEST_FIELDS = ("request_id", "request_type", "requested_at", "user_input")
REQUIRED_ORDER_FIELDS = ("symbol", "side", "type")


def missing_fields(payload: Dict[str, Any], fields: Iterable[str]) -> List[str]:
    return [field for field in fields if field not in payload or payload[field] in (None, "")]


def validate_request_context(request_context: JsonDict) -> List[str]:
    missing = missing_fields(request_context, REQUIRED_REQUEST_FIELDS)
    user_input = request_context.get("user_input")
    if not isinstance(user_input, dict):
        missing.append("user_input")
        return missing
    missing.extend("user_input.%s" % field for field in missing_fields(user_input, REQUIRED_ORDER_FIELDS))
    has_quantity = bool(user_input.get("quantity") or user_input.get("quoteOrderQty"))
    if not has_quantity:
        missing.append("user_input.quantity_or_quoteOrderQty")
    return missing


def assert_contract_state(state: AgentState) -> None:
    if state.get("lifecycle_status") == PASS_ACTION:
        raise AssertionError("PASS must not be used as lifecycle_status")
    if state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return
    trace = state.get("decision_trace", {})
    for stage in TRACE_STAGES:
        if stage not in trace:
            raise AssertionError("missing trace stage: %s" % stage)
        entry = trace[stage]
        for field in ("reason_codes", "evidence_refs", "final_action"):
            if field not in entry:
                raise AssertionError("missing trace.%s.%s" % (stage, field))
