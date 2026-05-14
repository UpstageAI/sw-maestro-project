from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any


_llm_schema_metrics: dict[str, dict[str, int]] = defaultdict(lambda: {"passed": 0, "failed": 0})
_policy_violation_metrics: dict[str, int] = defaultdict(int)
_llm_call_metrics: dict[str, int] = defaultdict(int)
_agent_failure_metrics: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
_llm_raw_responses: list[dict[str, Any]] = []
_llm_safety_metrics: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"passed": 0, "blocked": 0, "blocked_by_reason": defaultdict(int)}
)
_RAW_RESPONSE_RETENTION_DAYS = 7


def record_llm_schema_result(purpose: str, passed: bool) -> None:
    bucket = _llm_schema_metrics[purpose]
    if passed:
        bucket["passed"] += 1
    else:
        bucket["failed"] += 1


def llm_schema_summary() -> dict:
    by_purpose = {}
    total_passed = 0
    total_failed = 0
    for purpose, values in sorted(_llm_schema_metrics.items()):
        passed = values["passed"]
        failed = values["failed"]
        total = passed + failed
        total_passed += passed
        total_failed += failed
        by_purpose[purpose] = {
            "passed": passed,
            "failed": failed,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else None,
        }
    total = total_passed + total_failed
    return {
        "passed": total_passed,
        "failed": total_failed,
        "total": total,
        "pass_rate": round(total_passed / total, 4) if total else None,
        "by_purpose": by_purpose,
    }


def reset_llm_schema_metrics() -> None:
    _llm_schema_metrics.clear()


def record_policy_violation(filter_name: str) -> None:
    _policy_violation_metrics[filter_name] += 1


def policy_violation_summary() -> dict:
    by_filter = dict(sorted(_policy_violation_metrics.items()))
    return {"total": sum(by_filter.values()), "by_filter": by_filter}


def reset_policy_violation_metrics() -> None:
    _policy_violation_metrics.clear()


def record_llm_call(purpose: str) -> None:
    _llm_call_metrics[purpose] += 1


def llm_call_summary() -> dict:
    by_purpose = dict(sorted(_llm_call_metrics.items()))
    return {"total": sum(by_purpose.values()), "by_purpose": by_purpose}


def reset_llm_call_metrics() -> None:
    _llm_call_metrics.clear()


def record_llm_raw_response(purpose: str, response_body: dict[str, Any]) -> None:
    _prune_llm_raw_responses()
    _llm_raw_responses.append(
        {
            "recorded_at": datetime.now(UTC).isoformat(),
            "purpose": purpose,
            "response": response_body,
        }
    )


def llm_raw_response_summary() -> dict:
    _prune_llm_raw_responses()
    by_purpose: dict[str, int] = defaultdict(int)
    for item in _llm_raw_responses:
        by_purpose[item["purpose"]] += 1
    return {
        "total": len(_llm_raw_responses),
        "retention_days": _RAW_RESPONSE_RETENTION_DAYS,
        "by_purpose": dict(sorted(by_purpose.items())),
        "oldest_recorded_at": _llm_raw_responses[0]["recorded_at"] if _llm_raw_responses else None,
        "newest_recorded_at": _llm_raw_responses[-1]["recorded_at"] if _llm_raw_responses else None,
    }


def reset_llm_raw_responses() -> None:
    _llm_raw_responses.clear()


def record_llm_safety_result(purpose: str, passed: bool, reason: str = "ok") -> None:
    bucket = _llm_safety_metrics[purpose]
    if passed:
        bucket["passed"] += 1
        return
    bucket["blocked"] += 1
    bucket["blocked_by_reason"][reason] += 1


def llm_safety_summary() -> dict:
    by_purpose = {}
    total_passed = 0
    total_blocked = 0
    for purpose, values in sorted(_llm_safety_metrics.items()):
        passed = values["passed"]
        blocked = values["blocked"]
        total = passed + blocked
        total_passed += passed
        total_blocked += blocked
        by_purpose[purpose] = {
            "passed": passed,
            "blocked": blocked,
            "total": total,
            "pass_rate": round(passed / total, 4) if total else None,
            "blocked_rate": round(blocked / total, 4) if total else None,
            "blocked_by_reason": dict(sorted(values["blocked_by_reason"].items())),
        }
    total = total_passed + total_blocked
    return {
        "passed": total_passed,
        "blocked": total_blocked,
        "total": total,
        "pass_rate": round(total_passed / total, 4) if total else None,
        "blocked_rate": round(total_blocked / total, 4) if total else None,
        "by_purpose": by_purpose,
    }


def reset_llm_safety_metrics() -> None:
    _llm_safety_metrics.clear()


def _prune_llm_raw_responses() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=_RAW_RESPONSE_RETENTION_DAYS)
    _llm_raw_responses[:] = [
        item
        for item in _llm_raw_responses
        if datetime.fromisoformat(item["recorded_at"]) >= cutoff
    ]


def record_agent_failure(agent: str, reason: str) -> None:
    _agent_failure_metrics[agent][reason] += 1


def agent_failure_summary() -> dict:
    by_agent = {
        agent: dict(sorted(reasons.items()))
        for agent, reasons in sorted(_agent_failure_metrics.items())
    }
    total = sum(count for reasons in by_agent.values() for count in reasons.values())
    return {"total": total, "by_agent": by_agent}


def reset_agent_failure_metrics() -> None:
    _agent_failure_metrics.clear()
