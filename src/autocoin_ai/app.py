"""Public application service for standalone runs and resume."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping

from autocoin_ai.constants import LIFECYCLE_BE_REJECTED, LIFECYCLE_FAILED, LIFECYCLE_HOLD, LIFECYCLE_READY_FOR_BE, LIFECYCLE_REPORT_READY
from autocoin_ai.graph import build_agentic_order_graph, build_completion_graph, build_order_graph
from autocoin_ai.models import AgentState, ensure_state_shape
from autocoin_ai.run_store import JsonFileRunStore
from autocoin_ai.validators import assert_contract_state


class AutocoinAgentApp:
    def __init__(self, run_store: JsonFileRunStore | None = None) -> None:
        self.order_graph = build_order_graph()
        self.agentic_order_graph = build_agentic_order_graph()
        self.completion_graph = build_completion_graph()
        self._run_store = run_store
        self._runs: Dict[str, AgentState] = run_store.load_runs() if run_store else {}

    def _persist_runs(self) -> None:
        if self._run_store is not None:
            self._run_store.save_runs(self._runs)

    def start(self, state: Mapping[str, Any]) -> AgentState:
        return self._start_with_graph(state, self.order_graph)

    def start_agentic(self, state: Mapping[str, Any]) -> AgentState:
        return self._start_with_graph(state, self.agentic_order_graph)

    def _start_with_graph(self, state: Mapping[str, Any], graph: Any) -> AgentState:
        run_id = state.get("run_id")
        if not run_id:
            raise ValueError("run_id is required")
        prepared = ensure_state_shape(state)
        result = graph.invoke(prepared, config={"configurable": {"thread_id": run_id}})
        checked = ensure_state_shape(result)
        assert_contract_state(checked)
        self._runs[run_id] = deepcopy(checked)
        self._persist_runs()
        return checked

    def resume(self, run_id: str, patch_fields: Dict[str, object], resume_reason: str) -> AgentState:
        if run_id not in self._runs:
            raise ValueError("unknown run_id: %s" % run_id)
        previous = deepcopy(self._runs[run_id])
        if previous.get("trader_id"):
            raise ValueError("resume not supported for agentic runs in MVP")
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
        self._persist_runs()
        return checked

    def order_checkpoint_evidence(self, run_id: str) -> Dict[str, Any]:
        previous = self._require_run(run_id)
        graph = self.agentic_order_graph if previous.get("trader_id") else self.order_graph
        config = {"configurable": {"thread_id": run_id}}
        snapshot = graph.get_state(config)
        history = list(graph.get_state_history(config))
        return _checkpoint_evidence(snapshot.values, history)

    def completion_checkpoint_evidence(self, run_id: str) -> Dict[str, Any]:
        previous = self._require_run(run_id)
        if previous.get("lifecycle_status") not in (LIFECYCLE_REPORT_READY, LIFECYCLE_BE_REJECTED):
            raise ValueError("completion checkpoint not available before completion has executed")
        config = {"configurable": {"thread_id": run_id}}
        snapshot = self.completion_graph.get_state(config)
        history = list(self.completion_graph.get_state_history(config))
        return _checkpoint_evidence(snapshot.values, history)

    def _require_run(self, run_id: str) -> AgentState:
        if run_id not in self._runs:
            raise ValueError("unknown run_id: %s" % run_id)
        return deepcopy(self._runs[run_id])


def _checkpoint_evidence(values: Mapping[str, Any], history: List[Any]) -> Dict[str, Any]:
    return {
        "final_snapshot_lifecycle_status": values.get("lifecycle_status"),
        "history_snapshot_count": len(history),
    }
