"""Run one sample through the graph and print node-level quality artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import graph
from scripts.run_brief_eval import BRIEFS


def _flag_summary(report) -> str:
    if report is None:
        return "none"
    parts = [f"{flag.severity}:{flag.code}:{flag.point_id or '-'}" for flag in report.flags]
    return ", ".join(parts) if parts else "clean"


def run(sample_key: str) -> int:
    if sample_key not in BRIEFS:
        print(f"unknown sample: {sample_key}")
        return 2
    result = {}
    print(f"SAMPLE {sample_key}")
    for chunk in graph.stream({"raw_input": BRIEFS[sample_key]}, stream_mode="updates"):
        for node_name, update in chunk.items():
            keys = [key for key, value in (update or {}).items() if value is not None]
            print(f"NODE {node_name}: {', '.join(keys) if keys else '-'}")
            if update:
                result.update(update)
    print("\nQUALITY")
    for key in ("opinion_quality_a", "opinion_quality_b", "review_quality_a", "review_quality_b"):
        print(f"{key}: {_flag_summary(result.get(key))}")
    print("\nFINAL")
    print((result.get("final_review_text") or "")[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1] if len(sys.argv) > 1 else "farm_direct"))
