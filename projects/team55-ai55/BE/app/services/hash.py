from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from app.schemas import ProjectSnapshot


def _normalize_timestamps(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_timestamps(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_timestamps(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return value
        return parsed.replace(microsecond=0).isoformat()
    return value


def compute_snapshot_hash(snapshot: ProjectSnapshot) -> str:
    canonical_obj = _normalize_timestamps(snapshot.model_dump(mode="json"))
    canonical = json.dumps(canonical_obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()

