from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.agents.risk import run_risk
from app.agents.schedule import has_hard_overlap, run_schedule
from app.orchestrator import analyze_snapshot
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ApproveScheduleRequest,
    ApproveScheduleResponse,
    EventRejected,
    InternalCalendarEvent,
    Milestone,
    MilestoneApproveRequest,
    MilestoneApproveResponse,
    MilestoneStatus,
    MilestoneSuggestRequest,
    MilestoneSuggestResponse,
    Project,
    ProjectCreate,
    RiskSimulateRequest,
    RiskSimulateResponse,
    ProjectSnapshot,
)
from app.services.cache import analyze_cache, health_cache, milestone_cache
from app.services.hash import compute_snapshot_hash
from app.services.id_minter import mint_event_id, mint_milestone_id, mint_project_id
from app.services.llm_client import llm_client
from app.services.milestone_suggester import build_task_signature, suggest_project_milestones
from app.services.metrics import (
    agent_failure_summary,
    llm_call_summary,
    llm_raw_response_summary,
    llm_safety_summary,
    llm_schema_summary,
    policy_violation_summary,
    record_llm_call,
    record_llm_schema_result,
)


router = APIRouter()


def get_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _api_error(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


@router.post("/v1/projects", status_code=201, response_model=Project)
async def create_project(req: ProjectCreate) -> Project:
    return Project(project_id=mint_project_id(), **req.model_dump())


@router.post("/v1/projects/{project_id}/milestones:suggest", response_model=MilestoneSuggestResponse)
async def suggest_milestones(
    project_id: str,
    req: MilestoneSuggestRequest,
    now: datetime = Depends(get_now),
) -> MilestoneSuggestResponse:
    goal_hash = hashlib.sha256(req.snapshot.project.goal.encode()).hexdigest()
    cache_key = (
        "milestones",
        "v2.1",
        project_id,
        goal_hash,
        req.snapshot.project.starts_at.isoformat(),
        req.snapshot.project.ends_at.isoformat(),
        req.max_milestones,
        build_task_signature(req.snapshot),
    )
    cached = await milestone_cache.get(cache_key)
    if cached:
        return cached

    started = time.perf_counter()
    if llm_client.configured:
        record_llm_call("milestone_suggest")
    proposed, schema_success = await suggest_project_milestones(req.snapshot, req.max_milestones, llm_client)
    if schema_success is not None:
        record_llm_schema_result("milestone_suggest", schema_success)

    response = MilestoneSuggestResponse(
        project_id=project_id,
        proposed_milestones=proposed,
        agent_meta={"latency_ms": round((time.perf_counter() - started) * 1000), "tokens": 0},
    )
    await milestone_cache.put(cache_key, response, ttl=86400)
    return response


@router.post("/v1/projects/{project_id}/milestones:approve", response_model=MilestoneApproveResponse)
async def approve_milestones(
    project_id: str,
    req: MilestoneApproveRequest,
    now: datetime = Depends(get_now),
) -> MilestoneApproveResponse:
    milestones = [
        Milestone(
            milestone_id=mint_milestone_id(),
            project_id=project_id,
            name=item.name,
            due_date=item.due_date,
            status=MilestoneStatus.approved,
            ai_rationale=item.ai_rationale,
            approved_at=now,
        )
        for item in req.approved
    ]
    return MilestoneApproveResponse(milestones=milestones)


@router.post("/v1/projects/{project_id}/analyze", response_model=AnalyzeResponse)
async def analyze(
    project_id: str,
    req: AnalyzeRequest,
    now: datetime = Depends(get_now),
) -> AnalyzeResponse:
    tasks_by_id = {task.task_id: task for task in req.snapshot.tasks}
    decomposition_missing_estimate = [
        task_id
        for task_id in req.options.request_decomposition_for
        if tasks_by_id.get(task_id) is not None and tasks_by_id[task_id].estimated_hours is None
    ]
    if decomposition_missing_estimate:
        return _api_error(
            422,
            "task_info_insufficient",
            "Task 분해를 요청하려면 예상 소요시간을 먼저 입력해 주세요.",
            {"task_ids": decomposition_missing_estimate, "fields": ["estimated_hours"]},
        )

    snapshot_hash = compute_snapshot_hash(req.snapshot)
    cache_key = ("analyze", project_id, snapshot_hash)
    cached = await analyze_cache.get(cache_key)
    if cached:
        cached_meta = cached.meta.model_copy(update={"cache_hit": True})
        return cached.model_copy(update={"meta": cached_meta})

    response = await analyze_snapshot(project_id=project_id, snapshot=req.snapshot, options=req.options, now=now)
    object.__setattr__(response, "_snapshot", req.snapshot)
    await analyze_cache.put(cache_key, response, ttl=3600)
    return response


@router.post("/v1/projects/{project_id}/schedule:approve", response_model=ApproveScheduleResponse)
async def approve_schedule(
    project_id: str,
    req: ApproveScheduleRequest,
    now: datetime = Depends(get_now),
):
    cached = await analyze_cache.find_analyze_by_hash(project_id, req.snapshot_hash)
    if cached is None:
        return _api_error(409, "snapshot_hash_stale", "분석 결과가 만료되었습니다. 재분석 후 다시 승인해주세요.")

    original_snapshot = getattr(cached, "_snapshot", None)

    events_created: list[InternalCalendarEvent] = []
    events_rejected: list[EventRejected] = []
    proposals = {item.task_id: item for item in cached.schedule.slot_proposals}

    # Reconstruct the minimum task lookup from schedule proposals when snapshot is unavailable.
    snapshot_tasks = {task.task_id: task for task in original_snapshot.tasks} if original_snapshot else {}
    calendar_events = list(original_snapshot.calendar_events) if original_snapshot else []

    for approval in req.approvals:
        proposal = proposals.get(approval.task_id)
        if proposal is None:
            events_rejected.append(EventRejected(task_id=approval.task_id, reason="task_not_found"))
            continue
        if approval.candidate_slot_index >= len(proposal.candidate_slots):
            events_rejected.append(EventRejected(task_id=approval.task_id, reason="candidate_index_out_of_range"))
            continue
        slot = proposal.candidate_slots[approval.candidate_slot_index]
        task = snapshot_tasks.get(approval.task_id)
        raw_blocks = (
            [{"starts_at": approval.override_starts_at, "ends_at": approval.override_ends_at}]
            if approval.override_starts_at and approval.override_ends_at
            else [block.model_dump() for block in (slot.time_blocks or [])]
        ) or [{"starts_at": slot.starts_at, "ends_at": slot.ends_at}]
        candidate_events: list[InternalCalendarEvent] = []
        rejected_reason = None
        for block in raw_blocks:
            starts_at = block["starts_at"]
            ends_at = block["ends_at"]
            if ends_at <= starts_at:
                rejected_reason = "invalid_override_range"
                break
            if task and has_hard_overlap(
                task=task,
                starts_at=starts_at,
                ends_at=ends_at,
                calendar_events=[*calendar_events, *events_created, *candidate_events],
            ):
                rejected_reason = "override_conflicts"
                break
            candidate_events.append(
                InternalCalendarEvent(
                    event_id=mint_event_id(),
                    project_id=project_id,
                    task_id=approval.task_id,
                    assignee_id=task.assignee_id if task else None,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    approved=True,
                    approved_at=now,
                    source="ai_suggested",
                )
            )
        if rejected_reason:
            events_rejected.append(EventRejected(task_id=approval.task_id, reason=rejected_reason))
            continue
        events_created.extend(candidate_events)

    return ApproveScheduleResponse(events_created=events_created, events_rejected=events_rejected)


@router.post("/v1/projects/{project_id}/risk:simulate", response_model=RiskSimulateResponse)
async def simulate_risk(
    project_id: str,
    req: RiskSimulateRequest,
    now: datetime = Depends(get_now),
) -> RiskSimulateResponse:
    priority = await __import__("app.agents.priority", fromlist=["run_priority"]).run_priority(req.snapshot, now, [], use_llm=False)
    schedule = await run_schedule(req.snapshot, priority, now, use_llm=False)
    before = await run_risk(req.snapshot, priority, schedule, now, use_llm=False)
    suggestion_by_id = {item.id: item for item in before.suggestions}
    applied_suggestions = [suggestion_by_id[item] for item in req.applied_suggestion_ids if item in suggestion_by_id]
    simulated_snapshot = _apply_risk_suggestions(req.snapshot, applied_suggestions)
    after_priority = await __import__("app.agents.priority", fromlist=["run_priority"]).run_priority(simulated_snapshot, now, [], use_llm=False)
    after_schedule = await run_schedule(simulated_snapshot, after_priority, now, use_llm=False)
    after = await run_risk(simulated_snapshot, after_priority, after_schedule, now, use_llm=False)
    before_checks = {item.id: item.result for item in before.checks}
    changed_check_ids = [item.id for item in after.checks if before_checks.get(item.id) != item.result]
    changed_to_pass_ids = [
        item.id
        for item in after.checks
        if before_checks.get(item.id) == "fail" and item.result == "pass"
    ]
    before_scores = {item.task_id: item.score for item in priority.tasks_priority}
    after_scores = {item.task_id: item.score for item in after_priority.tasks_priority}
    applied_actions = [suggestion.action.model_dump(by_alias=True, exclude_none=True) for suggestion in applied_suggestions]
    target_task_ids = [
        action["target_task_id"]
        for action in applied_actions
        if isinstance(action.get("target_task_id"), str)
    ]
    priority_delta_by_task = {
        task_id: after_scores.get(task_id, 0) - before_scores.get(task_id, 0)
        for task_id in dict.fromkeys(target_task_ids)
    }
    priority_delta = max(priority_delta_by_task.values(), default=0)
    return RiskSimulateResponse(
        project_id=project_id,
        applied_suggestion_ids=req.applied_suggestion_ids,
        before=before,
        after=after,
        changed_check_ids=changed_check_ids,
        score_action_coherence={
            "priority_delta": priority_delta,
            "priority_delta_by_task": priority_delta_by_task,
            "changed_to_pass_ids": changed_to_pass_ids,
            "passes_threshold": priority_delta >= 5 and bool(changed_to_pass_ids),
        },
    )


@router.get("/v1/health")
async def health():
    cached = await health_cache.get("health:upstage")
    if cached:
        return {
            **cached,
            "llm_schema": llm_schema_summary(),
            "policy_violations": policy_violation_summary(),
            "llm_calls": llm_call_summary(),
            "llm_raw_responses": llm_raw_response_summary(),
            "llm_safety": llm_safety_summary(),
            "agent_failures": agent_failure_summary(),
        }
    value = {
        "status": "ok",
        "upstage_api": await llm_client.health(),
        "llm_schema": llm_schema_summary(),
        "policy_violations": policy_violation_summary(),
        "llm_calls": llm_call_summary(),
        "llm_raw_responses": llm_raw_response_summary(),
        "llm_safety": llm_safety_summary(),
        "agent_failures": agent_failure_summary(),
    }
    await health_cache.put("health:upstage", value, ttl=30)
    return value


def _apply_risk_suggestions(snapshot: ProjectSnapshot, suggestions) -> ProjectSnapshot:
    updated = snapshot.model_copy(deep=True)
    tasks = {task.task_id: task for task in updated.tasks}
    for suggestion in suggestions:
        action = suggestion.action.model_dump(by_alias=True, exclude_none=True)
        task_id = action.get("target_task_id")
        task = tasks.get(task_id) if task_id else None
        if task is None:
            continue
        if action.get("type") == "reassign":
            task.assignee_id = action.get("to") or task.assignee_id
        elif action.get("type") == "reschedule" and action.get("to"):
            try:
                task.deadline = datetime.fromisoformat(action["to"])
            except ValueError:
                continue
        elif action.get("type") == "raise_importance":
            task.importance = "critical"
        elif action.get("type") == "lower_importance":
            task.importance = "medium"
        elif action.get("type") == "add_predecessor" and action.get("to"):
            task.predecessor_ids = list(dict.fromkeys([*task.predecessor_ids, action["to"]]))
        elif action.get("type") == "remove_predecessor" and action.get("to"):
            task.predecessor_ids = [item for item in task.predecessor_ids if item != action["to"]]
    return updated
