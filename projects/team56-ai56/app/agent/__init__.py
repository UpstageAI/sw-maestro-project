from __future__ import annotations

import os
from pathlib import Path


def _bootstrap_env() -> None:
    project_root = Path(__file__).resolve().parents[2]

    env_path = project_root / ".env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))

    defaults = {
        "HIREPROOF_DATA_DIR": project_root / "data",
        "HIREPROOF_UPLOADS_DIR": project_root / "data" / "uploads",
        "HIREPROOF_ARTIFACTS_DIR": project_root / "data" / "artifacts",
        "HIREPROOF_SQLITE_PATH": project_root / "data" / "artifacts" / "hireproof.db",
    }
    for key, path in defaults.items():
        os.environ.setdefault(key, str(path))


_bootstrap_env()

from app.agent.graph import get_compiled_graph  # noqa: E402
from app.agent.nodes import get_pipeline  # noqa: E402

__all__ = ["get_compiled_graph", "get_pipeline"]
