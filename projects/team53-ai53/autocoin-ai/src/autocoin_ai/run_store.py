from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

from autocoin_ai.models import AgentState, ensure_state_shape, state_copy
from autocoin_ai.validators import assert_contract_state


class JsonFileRunStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    @classmethod
    def from_env(cls) -> "JsonFileRunStore":
        raw_path = os.getenv("AUTOCOIN_AI_RUNS_FILE", ".runtime/autocoin-ai-runs.json")
        return cls(Path(raw_path))

    def load_runs(self) -> dict[str, AgentState]:
        if not self.file_path.exists():
            return {}

        try:
            payload = json.loads(self.file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid run store file: {self.file_path}") from exc

        if not isinstance(payload, dict):
            raise ValueError(f"invalid run store payload: {self.file_path}")

        runs_payload = payload.get("runs", {})
        if not isinstance(runs_payload, dict):
            raise ValueError(f"invalid run store runs payload: {self.file_path}")

        runs: dict[str, AgentState] = {}
        for run_id, state in runs_payload.items():
            if not isinstance(run_id, str) or not isinstance(state, dict):
                raise ValueError(f"invalid run entry in store: {self.file_path}")
            normalized = ensure_state_shape(state)
            assert_contract_state(normalized)
            runs[run_id] = state_copy(normalized)

        return runs

    def save_runs(self, runs: Mapping[str, AgentState]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        serialized_runs = {
            run_id: state_copy(state)
            for run_id, state in runs.items()
        }
        payload = {"runs": serialized_runs}
        temp_path = self.file_path.with_suffix(f"{self.file_path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.file_path)
