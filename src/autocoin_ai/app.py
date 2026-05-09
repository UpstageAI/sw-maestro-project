"""Public application service for standalone runs and resume."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping

from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_HOLD, LIFECYCLE_READY_FOR_BE
from autocoin_ai.graph import build_completion_graph, build_order_graph
from autocoin_ai.models import AgentState, ensure_state_shape
from autocoin_ai.validators import assert_contract_state


class AutocoinAgentApp:
    def __init__(self) -> None:
        self.order_graph = build_order_graph()
        self.completion_graph = build_completion_graph()
        self._runs: Dict[str, AgentState] = {}

    def start(self, state: Mapping[str, Any]) -> AgentState:
        run_id = state.get("run_id")
        if not run_id:
            raise ValueError("run_id is required")
        prepared = ensure_state_shape(state)
        result = self.order_graph.invoke(prepared, config={"configurable": {"thread_id": run_id}})
        checked = ensure_state_shape(result)
        assert_contract_state(checked)
        self._runs[run_id] = deepcopy(checked)
        return checked

    def resume(self, run_id: str, patch_fields: Dict[str, object], resume_reason: str) -> AgentState:
        if run_id not in self._runs:
            raise ValueError("unknown run_id: %s" % run_id)
        previous = deepcopy(self._runs[run_id])
        if previous.get("lifecycle_status") == LIFECYCLE_FAILED:
            raise ValueError("FAILED runs cannot be resumed with the same run_id")
        if previous.get("lifecycle_status") != LIFECYCLE_HOLD:
            raise ValueError("only HOLD runs can be resumed")
        previous.setdefault("resume_history", []).append({"resume_reason": resume_reason, "patch_fields": deepcopy(patch_fields)})
        previous.setdefault("decision_trace_history", []).append(
            {
                "decision_trace": deepcopy(previous.get("decision_trace", {})),
                "verification_checks_count": len(previous.get("verification_checks", [])),
            }
        )
        result = self.start(previous)
        return result

    def complete(self, run_id: str, completion_payload: Dict[str, Any]) -> AgentState:
        if run_id not in self._runs:
            raise ValueError("unknown run_id: %s" % run_id)
        previous = deepcopy(self._runs[run_id])
        if previous.get("lifecycle_status") != LIFECYCLE_READY_FOR_BE:
            raise ValueError("only READY_FOR_BE runs can be completed")
        previous["completion_payload"] = deepcopy(completion_payload)
        result = self.completion_graph.invoke(previous, config={"configurable": {"thread_id": run_id}})
        checked = ensure_state_shape(result)
        assert_contract_state(checked)
        self._runs[run_id] = deepcopy(checked)
        return checked

    def order_checkpoint_evidence(self, run_id: str) -> Dict[str, Any]:
        config = {"configurable": {"thread_id": run_id}}
        snapshot = self.order_graph.get_state(config)
        history = list(self.order_graph.get_state_history(config))
        return _checkpoint_evidence(snapshot.values, history)

    def completion_checkpoint_evidence(self, run_id: str) -> Dict[str, Any]:
        config = {"configurable": {"thread_id": run_id}}
        snapshot = self.completion_graph.get_state(config)
        history = list(self.completion_graph.get_state_history(config))
        return _checkpoint_evidence(snapshot.values, history)


def _checkpoint_evidence(values: Mapping[str, Any], history: List[Any]) -> Dict[str, Any]:
    return {
        "final_snapshot_lifecycle_status": values.get("lifecycle_status"),
        "history_snapshot_count": len(history),
    }
