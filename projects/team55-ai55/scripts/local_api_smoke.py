from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any


SEOUL = timezone(timedelta(hours=9))


def post(base_url: str, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any], float]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read()), (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as error:
        body = json.loads(error.read())
        return error.code, body, (time.perf_counter() - started) * 1000


def create_project(base_url: str, suffix: str) -> dict[str, Any]:
    status, project, _ = post(
        base_url,
        "/v1/projects",
        {
            "name": f"로컬 통합 QA {suffix}",
            "goal": "FE/BE 로컬 통신 계약 검증",
            "starts_at": "2026-05-07",
            "ends_at": "2026-06-30",
            "default_working_hours": {
                "weekday": {"start": "09:00", "end": "18:00", "enabled": True},
                "weekend": {"start": "10:00", "end": "16:00", "enabled": False},
            },
            "timezone": "Asia/Seoul",
        },
    )
    assert status == 201, project
    return project


def base_snapshot(project: dict[str, Any]) -> dict[str, Any]:
    now = datetime(2026, 5, 7, 9, 0, tzinfo=SEOUL)
    return {
        "project": project,
        "members": [
            {
                "member_id": "mem_SMOKE1",
                "name": "백엔드",
                "role": "Backend",
                "weekly_capacity_hours": 40,
                "available_hours": [
                    {"day_of_week": day, "start": "09:00", "end": "18:00"}
                    for day in range(5)
                ],
            },
            {
                "member_id": "mem_SMOKE2",
                "name": "프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [
                    {"day_of_week": day, "start": "09:00", "end": "18:00"}
                    for day in range(5)
                ],
            },
        ],
        "tasks": [
            task(
                project,
                "task_SMOKE001",
                "API 연결",
                "분석 API 연결",
                "mem_SMOKE1",
                now + timedelta(days=2),
                "critical",
                2,
            )
        ],
        "milestones": [],
        "calendar_events": [],
    }


def task(
    project: dict[str, Any],
    task_id: str,
    title: str,
    description: str,
    assignee_id: str | None,
    deadline: datetime | None,
    importance: str,
    estimated_hours: float | None,
    *,
    progress_percent: int = 0,
    status: str = "todo",
    predecessor_ids: list[str] | None = None,
    delay_reason: str | None = "검증용 입력",
) -> dict[str, Any]:
    created = datetime(2026, 5, 7, 9, 0, tzinfo=SEOUL).isoformat()
    return {
        "task_id": task_id,
        "project_id": project["project_id"],
        "milestone_id": None,
        "title": title,
        "description": description,
        "assignee_id": assignee_id,
        "deadline": deadline.isoformat() if deadline else None,
        "importance": importance,
        "estimated_hours": estimated_hours,
        "status": status,
        "progress_percent": progress_percent,
        "delay_reason": delay_reason,
        "predecessor_ids": predecessor_ids or [],
        "created_at": created,
        "updated_at": created,
    }


def analyze(base_url: str, project_id: str, snapshot: dict[str, Any]) -> tuple[dict[str, Any], float]:
    status, body, latency_ms = post(
        base_url,
        f"/v1/projects/{project_id}/analyze",
        {"snapshot": snapshot, "options": {"schedule_horizon_days": 14, "use_llm": False}},
    )
    assert status == 200, body
    return body, latency_ms


def scenario_1_happy_path(base_url: str) -> dict[str, Any]:
    project = create_project(base_url, "S1")
    snapshot = base_snapshot(project)
    deadline = datetime(2026, 5, 20, 18, 0, tzinfo=SEOUL)
    snapshot["tasks"] = [
        task(
            project,
            f"task_HAPPY{i:03d}",
            f"정상 시나리오 Task {i}",
            "정상 일정 검증",
            "mem_SMOKE1" if i % 2 else "mem_SMOKE2",
            deadline,
            "high" if i == 1 else "medium",
            1,
            progress_percent=40,
        )
        for i in range(1, 6)
    ]

    milestone_status, milestones, _ = post(
        base_url,
        f"/v1/projects/{project['project_id']}/milestones:suggest",
        {"snapshot": snapshot, "max_milestones": 3},
    )
    assert milestone_status == 200, milestones
    assert len(milestones["proposed_milestones"]) >= 1, milestones

    first, cold_ms = analyze(base_url, project["project_id"], snapshot)
    repeated = []
    cache_latencies = []
    for _ in range(4):
        item, latency_ms = analyze(base_url, project["project_id"], snapshot)
        repeated.append(item)
        cache_latencies.append(latency_ms)

    assert len(first["priority"]["tasks_priority"]) == 5, first
    assert len(first["schedule"]["slot_proposals"]) == 5, first
    assert len(first["risk"]["checks"]) == 3, first
    assert first["risk"]["blockers_failed"] == [], first["risk"]
    assert all(item["snapshot_hash"] == first["snapshot_hash"] for item in repeated), repeated
    assert all(item["meta"]["cache_hit"] is True for item in repeated), repeated
    assert all(item["priority"]["tasks_priority"] == first["priority"]["tasks_priority"] for item in repeated), repeated
    assert all(item["schedule"]["slot_proposals"] == first["schedule"]["slot_proposals"] for item in repeated), repeated
    assert all(item["risk"]["checks"] == first["risk"]["checks"] for item in repeated), repeated

    approve_status, approved, approve_ms = post(
        base_url,
        f"/v1/projects/{project['project_id']}/schedule:approve",
        {
            "snapshot_hash": first["snapshot_hash"],
            "approvals": [
                {"task_id": proposal["task_id"], "candidate_slot_index": proposal["selected_index"]}
                for proposal in first["schedule"]["slot_proposals"][:2]
            ],
        },
    )
    assert approve_status == 200, approved
    assert len(approved["events_created"]) == 2, approved
    assert all(event["approved"] for event in approved["events_created"]), approved

    return {
        "priority": len(first["priority"]["tasks_priority"]),
        "schedule": len(first["schedule"]["slot_proposals"]),
        "risk_checks": len(first["risk"]["checks"]),
        "milestones": len(milestones["proposed_milestones"]),
        "cache_hit": True,
        "cold_ms": round(cold_ms),
        "cache_p95_ms": round(max(cache_latencies)),
        "approve_ms": round(approve_ms),
    }


def scenario_2_unschedulable(base_url: str) -> dict[str, Any]:
    project = create_project(base_url, "S2")
    snapshot = base_snapshot(project)
    now = datetime(2026, 5, 7, 9, 0, tzinfo=SEOUL)
    snapshot["tasks"] = [
        task(project, "task_NOCAP001", "마감 전 8h 작업", "가용시간 부족 검증", "mem_SMOKE1", now.replace(hour=18), "critical", 8)
    ]
    snapshot["calendar_events"] = [
        {
            "event_id": "evt_BUSY0001",
            "project_id": project["project_id"],
            "task_id": "task_NOCAP001",
            "assignee_id": "mem_SMOKE1",
            "starts_at": now.replace(hour=13).isoformat(),
            "ends_at": now.replace(hour=17).isoformat(),
            "approved": True,
            "approved_at": now.isoformat(),
            "source": "external_blocking",
        }
    ]
    body, _ = analyze(base_url, project["project_id"], snapshot)
    reasons = body["schedule"]["unschedulable"][0]["reasons"]
    assert "no_capacity_before_deadline" in reasons, body["schedule"]
    return {"unschedulable": body["schedule"]["unschedulable"]}


def scenario_3_overload_unassigned(base_url: str) -> dict[str, Any]:
    project = create_project(base_url, "S3")
    snapshot = base_snapshot(project)
    snapshot["members"][0]["weekly_capacity_hours"] = 8
    snapshot["members"][1]["weekly_capacity_hours"] = 8
    deadline = datetime(2026, 5, 30, 18, 0, tzinfo=SEOUL)
    snapshot["tasks"] = [
        *[
            task(project, f"task_LOAD{i:04d}", f"쏠림 작업 {i}", "담당자 업무 쏠림 검증", "mem_SMOKE1", deadline, "high", 1.5)
            for i in range(6)
        ],
    ]
    body, _ = analyze(base_url, project["project_id"], snapshot)
    checks = {item["id"]: item["result"] for item in body["risk"]["checks"]}
    assert checks["workload_concentration"] == "fail", body["risk"]
    suggestion = next(item for item in body["risk"]["suggestions"] if "workload_concentration" in item["fixes_check_ids"])

    status, simulated, simulate_ms = post(
        base_url,
        f"/v1/projects/{project['project_id']}/risk:simulate",
        {"snapshot": snapshot, "applied_suggestion_ids": [suggestion["id"]]},
    )
    assert status == 200, simulated
    before_workload = next(item["result"] for item in simulated["before"]["checks"] if item["id"] == "workload_concentration")
    after_workload = next(item["result"] for item in simulated["after"]["checks"] if item["id"] == "workload_concentration")
    assert (before_workload, after_workload) == ("fail", "pass"), simulated
    coherence = simulated["score_action_coherence"]
    assert coherence["priority_delta"] >= 5, simulated
    assert coherence["passes_threshold"] is True, simulated
    return {
        "checks": {"workload_concentration": checks["workload_concentration"]},
        "risk_simulate_workload_concentration": [before_workload, after_workload],
        "score_action_coherence_delta": coherence["priority_delta"],
        "simulate_ms": round(simulate_ms),
    }


def scenario_4_circular_dependency(base_url: str) -> dict[str, Any]:
    project = create_project(base_url, "S4")
    snapshot = base_snapshot(project)
    now = datetime(2026, 5, 14, 18, 0, tzinfo=SEOUL)
    snapshot["tasks"] = [
        task(project, "task_CYCLE001", "순환 A", "순환 검증", "mem_SMOKE1", now, "high", 1, predecessor_ids=["task_CYCLE002"]),
        task(project, "task_CYCLE002", "순환 B", "순환 검증", "mem_SMOKE2", now, "high", 1, predecessor_ids=["task_CYCLE001"]),
    ]
    status, body, _ = post(base_url, f"/v1/projects/{project['project_id']}/analyze", {"snapshot": snapshot, "options": {"use_llm": False}})
    assert status == 200, body
    checks = {item["id"]: item["result"] for item in body["risk"]["checks"]}
    assert checks["dependency_correctness"] == "fail", body["risk"]
    assert "dependency_correctness" in body["risk"]["blockers_failed"], body["risk"]
    suggestion = next(item for item in body["risk"]["suggestions"] if "dependency_correctness" in item["fixes_check_ids"])
    assert suggestion["action"]["type"] == "remove_predecessor", body["risk"]
    assert suggestion["action"]["to"] in {"task_CYCLE001", "task_CYCLE002"}, body["risk"]
    return {
        "status": status,
        "checks": {"dependency_correctness": checks["dependency_correctness"]},
        "suggestion_action": suggestion["action"],
    }


def scenario_5_stale_hash(base_url: str) -> dict[str, Any]:
    project = create_project(base_url, "S5")
    snapshot = base_snapshot(project)
    snapshot["tasks"][0]["deadline"] = datetime(2026, 5, 20, 18, 0, tzinfo=SEOUL).isoformat()
    first, _ = analyze(base_url, project["project_id"], snapshot)
    snapshot["tasks"][0]["title"] = "API 연결 변경 후 재분석"
    fresh, _ = analyze(base_url, project["project_id"], snapshot)

    stale_status, stale, _ = post(
        base_url,
        f"/v1/projects/{project['project_id']}/schedule:approve",
        {"snapshot_hash": "stale", "approvals": [{"task_id": "task_SMOKE001", "candidate_slot_index": 0}]},
    )
    assert stale_status == 409, stale
    assert stale["error"]["code"] == "snapshot_hash_stale", stale
    assert first["snapshot_hash"] != fresh["snapshot_hash"], (first["snapshot_hash"], fresh["snapshot_hash"])

    fresh_status, approved, _ = post(
        base_url,
        f"/v1/projects/{project['project_id']}/schedule:approve",
        {"snapshot_hash": fresh["snapshot_hash"], "approvals": [{"task_id": "task_SMOKE001", "candidate_slot_index": 0}]},
    )
    assert fresh_status == 200, approved
    assert len(approved["events_created"]) == 1, approved
    return {"stale_status": stale_status, "fresh_approve_events": len(approved["events_created"])}


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    report = {
        "ok": True,
        "scenarios": {
            "1_happy_path": scenario_1_happy_path(base_url),
            "2_unschedulable": scenario_2_unschedulable(base_url),
            "3_overload_unassigned": scenario_3_overload_unassigned(base_url),
            "4_circular_dependency": scenario_4_circular_dependency(base_url),
            "5_stale_hash": scenario_5_stale_hash(base_url),
        },
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
