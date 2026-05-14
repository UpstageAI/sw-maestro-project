#!/usr/bin/env python3
"""docs/success_metrics.json 에 약속된 정적 지표값이 실제 코드와 일치하는지 검증.

사용:
    PYTHONPATH=$(pwd) python scripts/check_metrics.py

종료 코드:
    0 - 모든 정적 지표가 코드와 일치
    1 - 1건 이상 불일치 (CI 빌드 실패용)

검증 범위:
    런타임 측정이 필요한 응답 시간(response_time_*) 과 출력 길이
    (summary_output_length), 카테고리 라벨(fallback_strategy) 은 정적
    검증 대상에서 제외하고 7개 지표만 다룬다.
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.extractor import _KOREAN_SURNAMES, _NAME_BLOCKLIST, find_missed_agenda
from backend.llm import build_provider
from backend.schemas import MAX_AGENDA_LEN, MAX_TRANSCRIPT_LEN


def load_metrics() -> dict:
    path = ROOT / "docs" / "success_metrics.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {m["id"]: m for m in data["metrics"]}


def count_test_functions() -> int:
    total = 0
    for f in (ROOT / "backend" / "tests").glob("test_*.py"):
        total += len(re.findall(r"^def test_", f.read_text(encoding="utf-8"), re.MULTILINE))
    return total


def main() -> int:
    metrics = load_metrics()
    failures: list[str] = []

    def check_exact(metric_id: str, actual) -> None:
        expected = metrics[metric_id]["value"]
        ok = actual == expected
        tag = "[ OK ]" if ok else "[FAIL]"
        print(f"  {tag} {metric_id:40s} expected={expected!r:>15}  actual={actual!r}")
        if not ok:
            failures.append(f"{metric_id}: expected {expected!r}, got {actual!r}")

    def check_providers() -> None:
        metric_id = "supported_llm_providers"
        expected_count = metrics[metric_id]["value"]
        expected_names = set(metrics[metric_id]["providers"])
        src = inspect.getsource(build_provider).lower()
        found = {p for p in expected_names if p in src}
        ok = (len(found) == expected_count) and (found == expected_names)
        tag = "[ OK ]" if ok else "[FAIL]"
        print(f"  {tag} {metric_id:40s} expected={sorted(expected_names)}  found={sorted(found)}")
        if not ok:
            missing = expected_names - found
            failures.append(f"{metric_id}: missing {sorted(missing)} in build_provider")

    print("=" * 78)
    print(" 정적 성공 지표 검증 (docs/success_metrics.json <-> backend code)")
    print("=" * 78)

    check_exact("korean_surname_dict_size", len(_KOREAN_SURNAMES))
    check_exact("noun_blocklist_size", len(_NAME_BLOCKLIST))
    check_exact(
        "missed_agenda_jaccard_threshold",
        inspect.signature(find_missed_agenda).parameters["threshold"].default,
    )
    check_exact("agenda_max_length", MAX_AGENDA_LEN)
    check_exact("transcript_max_length", MAX_TRANSCRIPT_LEN)
    check_providers()
    check_exact("automated_test_count", count_test_functions())

    print("=" * 78)
    if failures:
        print(f"\n{len(failures)} 건 불일치:")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("\n모든 정적 지표가 코드와 일치합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
