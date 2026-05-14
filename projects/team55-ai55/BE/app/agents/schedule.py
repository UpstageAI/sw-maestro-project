"""
Schedule Agent — spec 03-agent-schedule-spec.md 준수 + 기존 회귀 테스트 호환 버전 (v2).

vs v1 변경:
  - task_blocks는 유지하되 후보 슬롯 길이는 estimated_hours 통째로 사용
    (회귀: 9h Task가 9h 윈도우에 1개 후보로 들어가야 함)
  - deadline_in_past 사유 추가 제거 (기존 코드와 동일하게 유지)
  - hard_overlap 슬롯은 폐기 (기존 동작 보존; 시나리오 2가 unschedulable 기대)
  - warning 형식: 모든 위반을 'rerank_violation:{task_id}'로 통일 (테스트 호환)
  - _working_window_for_member: 같은 날 다음 윈도우 탐색 보장
"""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta

from app.schemas import (
    CandidateSlot,
    CalendarEventSource,
    Conflict,
    InternalCalendarEvent,
    PriorityResponse,
    ProjectSnapshot,
    ScheduleBlock,
    ScheduleResponse,
    SlotProposal,
    SlotQuality,
    Task,
    TaskStatus,
    UnschedulableTask,
)
from app.services.llm_client import llm_client
from app.services.metrics import (
    record_llm_call,
    record_llm_safety_result,
    record_llm_schema_result,
    record_policy_violation,
)


FORBIDDEN_WORDS = (
    "매력", "호감", "인상", "성격", "잘생", "멋지",
    "게으", "느려", "의지", "무능", "책임감", "능력",
)

DEFAULT_MAX_CANDIDATES_PER_TASK = 3
DEFAULT_MIN_BLOCK_MINUTES = 30
DEFAULT_MAX_BLOCK_MINUTES = 240
HARD_OVERLAP_PENALTY = 30
DENSITY_BUCKET_LIMIT = 2
DENSITY_PENALTY_PER_EXTRA = 25


def _has_forbidden_words(text: str) -> bool:
    found = any(word in text for word in FORBIDDEN_WORDS)
    if found:
        record_policy_violation("forbidden_word")
    return found


def _time_from_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def task_blocks(
    estimated_hours: float,
    *,
    min_block_minutes: int = DEFAULT_MIN_BLOCK_MINUTES,
    max_block_minutes: int = DEFAULT_MAX_BLOCK_MINUTES,
) -> list[int]:
    """스펙 §9 — 분석/리포트 유틸. (후보 길이 결정엔 사용 안 함)"""
    total_min = int(round(estimated_hours * 60))
    if total_min <= 0:
        return []
    blocks: list[int] = []
    while total_min > 0:
        size = min(total_min, max_block_minutes)
        if size < min_block_minutes:
            size = min_block_minutes
        blocks.append(size)
        total_min -= size
    return blocks


def _next_window_start(snapshot: ProjectSnapshot, current: datetime) -> datetime:
    cursor = current.replace(second=0, microsecond=0)
    for _ in range(90):
        is_weekend = cursor.weekday() >= 5
        hour_range = (
            snapshot.project.default_working_hours.weekend
            if is_weekend
            else snapshot.project.default_working_hours.weekday
        )
        if not hour_range.enabled:
            cursor = (cursor + timedelta(days=1)).replace(hour=0, minute=0)
            continue
        start = datetime.combine(cursor.date(), _time_from_hhmm(hour_range.start), tzinfo=cursor.tzinfo)
        end = datetime.combine(cursor.date(), _time_from_hhmm(hour_range.end), tzinfo=cursor.tzinfo)
        if cursor < start:
            return start
        if start <= cursor < end:
            return cursor
        cursor = (cursor + timedelta(days=1)).replace(hour=0, minute=0)
    return current


def _working_window_for_member(
    snapshot: ProjectSnapshot, task: Task, current: datetime
) -> tuple[datetime, datetime] | None:
    """
    담당자별 working window. current 시각 이후 가장 가까운 윈도우 반환.
    같은 날 여러 윈도우가 있으면 그중 current가 들어갈 수 있는 첫 윈도우.
    """
    member = next((m for m in snapshot.members if m.member_id == task.assignee_id), None)
    if member:
        member_windows = sorted(
            (w for w in member.available_hours if w.day_of_week == current.weekday()),
            key=lambda w: w.start,
        )
        for w in member_windows:
            ws = datetime.combine(current.date(), _time_from_hhmm(w.start), tzinfo=current.tzinfo)
            we = datetime.combine(current.date(), _time_from_hhmm(w.end), tzinfo=current.tzinfo)
            if current < we:
                return ws, we
        if member_windows:
            return None

    is_weekend = current.weekday() >= 5
    hour_range = (
        snapshot.project.default_working_hours.weekend
        if is_weekend
        else snapshot.project.default_working_hours.weekday
    )
    if not hour_range.enabled:
        return None
    return (
        datetime.combine(current.date(), _time_from_hhmm(hour_range.start), tzinfo=current.tzinfo),
        datetime.combine(current.date(), _time_from_hhmm(hour_range.end), tzinfo=current.tzinfo),
    )


def _is_within_working_window(
    snapshot: ProjectSnapshot, task: Task, starts_at: datetime, ends_at: datetime
) -> bool:
    window = _working_window_for_member(snapshot, task, starts_at)
    if window is None:
        return False
    ws, we = window
    return ws <= starts_at and ends_at <= we


def _overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def _bucket_start(value: datetime) -> datetime:
    return value.replace(minute=0, second=0, microsecond=0)


def _project_density_penalty(starts_at: datetime, ends_at: datetime, events: list[InternalCalendarEvent]) -> int:
    bucket = _bucket_start(starts_at)
    bucket_end = bucket + timedelta(hours=1)
    overlapping_count = sum(
        1
        for event in events
        if event.source == "ai_suggested" and _overlap(bucket, bucket_end, event.starts_at, event.ends_at)
    )
    if overlapping_count < DENSITY_BUCKET_LIMIT:
        return 0
    return min(60, (overlapping_count - DENSITY_BUCKET_LIMIT + 1) * DENSITY_PENALTY_PER_EXTRA)


def detect_conflicts(
    *,
    task: Task,
    starts_at: datetime,
    ends_at: datetime,
    events: list[InternalCalendarEvent],
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    for event in events:
        if not (event.approved or event.source == CalendarEventSource.external_blocking):
            continue
        if not _overlap(starts_at, ends_at, event.starts_at, event.ends_at):
            continue
        kind = "hard_overlap" if event.assignee_id == task.assignee_id else "soft_overlap"
        conflicts.append(Conflict(event_id=event.event_id, kind=kind))
    return conflicts


def compute_fit_score(
    *,
    snapshot: ProjectSnapshot,
    task: Task,
    starts_at: datetime,
    ends_at: datetime,
    events: list[InternalCalendarEvent],
    has_hard_overlap: bool,
) -> tuple[int, float, bool]:
    """스펙 §6.2 + §6.4 페널티."""
    if task.deadline:
        slack_h = (task.deadline - ends_at).total_seconds() / 3600
        deadline_score = max(0.0, min(1.0, slack_h / 24))
    else:
        deadline_score = 0.5

    in_window = _is_within_working_window(snapshot, task, starts_at, ends_at)
    window_score = 1.0 if in_window else 0.2

    same_day_hours = sum(
        (e.ends_at - e.starts_at).total_seconds() / 3600
        for e in events
        if e.assignee_id == task.assignee_id and e.starts_at.date() == starts_at.date()
    )
    load_score = max(0.0, min(1.0, 1 - same_day_hours / 8))

    raw = 0.5 * deadline_score + 0.3 * window_score + 0.2 * load_score
    score = round(raw * 100)
    if has_hard_overlap:
        score = max(0, score - HARD_OVERLAP_PENALTY)
    score = max(0, score - _project_density_penalty(starts_at, ends_at, events))
    return score, deadline_score, in_window


def _classify_quality(
    *, in_window: bool, has_hard_overlap: bool, deadline_score: float
) -> SlotQuality:
    """스펙 §6.3."""
    if in_window and not has_hard_overlap and deadline_score >= 0.5:
        return SlotQuality.preferred
    if in_window and not has_hard_overlap and deadline_score >= 0.0:
        return SlotQuality.acceptable
    return SlotQuality.fallback


def _slot_blocks(slot: CandidateSlot) -> list[ScheduleBlock]:
    return slot.time_blocks or [ScheduleBlock(starts_at=slot.starts_at, ends_at=slot.ends_at)]


def _candidate_blocks_for_task(
    *,
    snapshot: ProjectSnapshot,
    task: Task,
    start_at: datetime,
    events: list[InternalCalendarEvent],
    horizon_end: datetime,
) -> tuple[list[ScheduleBlock], list[Conflict]] | None:
    if task.estimated_hours is None:
        return None

    blocks: list[ScheduleBlock] = []
    conflicts: list[Conflict] = []
    cursor = _next_window_start(snapshot, start_at)
    for block_minutes in task_blocks(task.estimated_hours):
        duration = timedelta(minutes=block_minutes)
        safety = 0
        while cursor < horizon_end:
            safety += 1
            if safety > 500:
                return None

            member_window = _working_window_for_member(snapshot, task, cursor)
            if member_window is None:
                cursor = _next_window_start(
                    snapshot, (cursor + timedelta(days=1)).replace(hour=0, minute=0)
                )
                continue

            window_start, window_end = member_window
            if cursor < window_start:
                cursor = window_start

            end = cursor + duration
            if end > window_end:
                cursor = _next_window_start(snapshot, window_end + timedelta(minutes=1))
                continue
            if task.deadline is not None and end > task.deadline:
                return None

            block_conflicts = detect_conflicts(
                task=task,
                starts_at=cursor,
                ends_at=end,
                events=events,
            )
            if any(conflict.kind == "hard_overlap" for conflict in block_conflicts):
                cursor = _next_window_start(snapshot, cursor + timedelta(minutes=30))
                continue

            conflicts.extend(block_conflicts)
            blocks.append(ScheduleBlock(starts_at=cursor, ends_at=end))
            cursor = _next_window_start(snapshot, end)
            break
        else:
            return None

    return blocks, conflicts


def _candidates_for_task(
    *,
    snapshot: ProjectSnapshot,
    task: Task,
    earliest: datetime,
    events: list[InternalCalendarEvent],
    horizon_end: datetime,
    max_candidates: int = DEFAULT_MAX_CANDIDATES_PER_TASK,
) -> list[CandidateSlot]:
    """
    Candidate 하나가 여러 근무 블록을 품을 수 있게 해서 10h/12h Task도
    하루 근무창을 넘는다는 이유만으로 미배치되지 않게 합니다.
    hard_overlap 슬롯은 폐기 (기존 동작 보존).
    """
    if task.estimated_hours is None:
        return []

    cursor = _next_window_start(snapshot, earliest)
    candidates: list[CandidateSlot] = []

    safety = 0
    while cursor < horizon_end and len(candidates) < max_candidates:
        safety += 1
        if safety > 500:
            break

        block_result = _candidate_blocks_for_task(
            snapshot=snapshot,
            task=task,
            start_at=cursor,
            events=events,
            horizon_end=horizon_end,
        )
        if block_result is None:
            cursor = _next_window_start(snapshot, cursor + timedelta(minutes=30))
            continue
        blocks, conflicts = block_result
        starts_at = blocks[0].starts_at
        ends_at = blocks[-1].ends_at
        has_hard = any(c.kind == "hard_overlap" for c in conflicts)
        scored_blocks = [
            compute_fit_score(
                snapshot=snapshot,
                task=task,
                starts_at=block.starts_at,
                ends_at=block.ends_at,
                events=events,
                has_hard_overlap=has_hard,
            )
            for block in blocks
        ]
        score = round(sum(item[0] for item in scored_blocks) / len(scored_blocks))
        deadline_score = (
            max(0.0, min(1.0, ((task.deadline - ends_at).total_seconds() / 3600) / 24))
            if task.deadline
            else 0.5
        )
        in_window = all(item[2] for item in scored_blocks)
        quality = _classify_quality(
            in_window=in_window, has_hard_overlap=has_hard, deadline_score=deadline_score
        )

        same_day_hours = sum(
            (e.ends_at - e.starts_at).total_seconds() / 3600
            for e in events
            if e.assignee_id == task.assignee_id and e.starts_at.date() == starts_at.date()
        )
        rationale_facts = [
            f"{starts_at.isoformat()}부터 {ends_at.isoformat()}까지 {len(blocks)}개 근무 블록으로 배치 가능",
            f"마감 여유 점수 {deadline_score:.2f}",
            f"근무가능시간 내 여부: {'예' if in_window else '아니오'}",
            f"당일 담당자 배정 {same_day_hours:.1f}h",
        ]

        candidates.append(
            CandidateSlot(
                starts_at=starts_at,
                ends_at=ends_at,
                time_blocks=blocks,
                quality=quality,
                fit_score=score,
                conflicts=conflicts,
                rationale_facts=rationale_facts,
            )
        )

        cursor = _next_window_start(snapshot, starts_at + timedelta(minutes=30))

    return candidates


def priority_aware_topo_sort(tasks: list[Task], priority_by_task: dict[str, int]) -> list[Task]:
    by_id = {task.task_id: task for task in tasks}
    indegree = {task.task_id: 0 for task in tasks}
    successors: dict[str, list[str]] = {}
    for task in tasks:
        for pred_id in task.predecessor_ids:
            if pred_id not in by_id:
                continue
            indegree[task.task_id] += 1
            successors.setdefault(pred_id, []).append(task.task_id)

    ready = [task_id for task_id, degree in indegree.items() if degree == 0]
    ordered: list[Task] = []
    while ready:
        ready.sort(key=lambda task_id: (-priority_by_task.get(task_id, 0), task_id))
        task_id = ready.pop(0)
        ordered.append(by_id[task_id])
        for next_id in sorted(successors.get(task_id, [])):
            indegree[next_id] -= 1
            if indegree[next_id] == 0:
                ready.append(next_id)
    return ordered if len(ordered) == len(tasks) else tasks


def validate_selected_schedule(
    *,
    snapshot: ProjectSnapshot,
    proposals: list[SlotProposal],
    enforce_density: bool = True,
) -> list[str]:
    task_by_id = {task.task_id: task for task in snapshot.tasks}
    violations: list[str] = []
    selected_by_task: dict[str, CandidateSlot] = {}

    for proposal in proposals:
        if proposal.selected_index < 0 or proposal.selected_index >= len(proposal.candidate_slots):
            violations.append(f"selected_index_oob:{proposal.task_id}")
            continue
        selected_by_task[proposal.task_id] = proposal.candidate_slots[proposal.selected_index]

    selected_items = list(selected_by_task.items())
    for index, (task_id, slot) in enumerate(selected_items):
        task = task_by_id.get(task_id)
        if task is None:
            violations.append(f"unknown_task:{task_id}")
            continue
        blocks = _slot_blocks(slot)
        if task.deadline is not None and blocks[-1].ends_at > task.deadline:
            violations.append(f"deadline_exceeded:{task_id}")
        if not all(_is_within_working_window(snapshot, task, block.starts_at, block.ends_at) for block in blocks):
            violations.append(f"working_window_violation:{task_id}")
        for pred_id in task.predecessor_ids:
            pred_slot = selected_by_task.get(pred_id)
            pred_blocks = _slot_blocks(pred_slot) if pred_slot is not None else []
            if pred_blocks and pred_blocks[-1].ends_at > blocks[0].starts_at:
                violations.append(f"dependency_inversion:{task_id}")
        for other_task_id, other_slot in selected_items[index + 1:]:
            other_task = task_by_id.get(other_task_id)
            if (
                other_task is not None
                and task.assignee_id == other_task.assignee_id
                and any(
                    _overlap(block.starts_at, block.ends_at, other_block.starts_at, other_block.ends_at)
                    for block in blocks
                    for other_block in _slot_blocks(other_slot)
                )
            ):
                violations.append(f"hard_overlap:{task_id}:{other_task_id}")

    if enforce_density:
        bucket_counts: dict[str, int] = {}
        for slot in selected_by_task.values():
            for block in _slot_blocks(slot):
                bucket = _bucket_start(block.starts_at).isoformat()
                bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        for bucket, count in bucket_counts.items():
            if count > DENSITY_BUCKET_LIMIT:
                violations.append(f"density_violation:{bucket}")

    return violations


def repair_schedule(
    *,
    snapshot: ProjectSnapshot,
    proposals: list[SlotProposal],
    max_rounds: int = 2,
) -> tuple[list[SlotProposal], list[str]]:
    repaired = list(proposals)
    if len(repaired) > 50:
        return repaired, validate_selected_schedule(
            snapshot=snapshot,
            proposals=repaired,
            enforce_density=False,
        )
    for _ in range(max_rounds):
        violations = validate_selected_schedule(snapshot=snapshot, proposals=repaired)
        if not violations:
            return repaired, []

        changed = False
        best_trial = repaired
        best_violations = violations
        for proposal_index, proposal in enumerate(repaired):
            for candidate_index in range(len(proposal.candidate_slots)):
                if candidate_index == proposal.selected_index:
                    continue
                trial = list(repaired)
                trial[proposal_index] = proposal.model_copy(update={"selected_index": candidate_index})
                trial_violations = validate_selected_schedule(snapshot=snapshot, proposals=trial)
                if not trial_violations:
                    repaired = trial
                    changed = True
                    break
                if len(trial_violations) < len(best_violations):
                    best_trial = trial
                    best_violations = trial_violations
            if changed:
                break

        if changed:
            continue
        if len(best_violations) < len(violations):
            repaired = best_trial
            continue
        return repaired, violations

    return repaired, validate_selected_schedule(snapshot=snapshot, proposals=repaired)


def _apply_priority_assignments(snapshot: ProjectSnapshot, priority: PriorityResponse) -> None:
    task_by_id = {task.task_id: task for task in snapshot.tasks}
    for assignment in priority.task_assignments:
        task = task_by_id.get(assignment.task_id)
        if task is None:
            continue
        if task.assignee_id is None and task.status in (TaskStatus.todo, TaskStatus.in_progress):
            task.assignee_id = assignment.assignee_id


def _reason_for_validation_violation(violation: str) -> str:
    if violation.startswith("dependency_inversion:"):
        return "predecessor_incomplete"
    return "no_capacity_before_deadline"


def _task_ids_from_validation_violation(violation: str) -> list[str]:
    parts = violation.split(":")
    if len(parts) < 2:
        return []
    if parts[0] == "hard_overlap" and len(parts) >= 3:
        return [parts[2]]
    if parts[0] == "density_violation":
        return []
    return [parts[1]]


def finalize_valid_schedule(
    *,
    snapshot: ProjectSnapshot,
    proposals: list[SlotProposal],
    unschedulable: list[UnschedulableTask],
    warnings: list[str],
) -> tuple[list[SlotProposal], list[UnschedulableTask], list[str]]:
    final_proposals = list(proposals)
    final_unschedulable = list(unschedulable)
    final_warnings = list(warnings)
    already_unschedulable = {item.task_id for item in final_unschedulable}

    while True:
        violations = [
            violation
            for violation in validate_selected_schedule(snapshot=snapshot, proposals=final_proposals)
            if not violation.startswith("density_violation:")
        ]
        if not violations:
            return final_proposals, final_unschedulable, final_warnings

        remove_by_task: dict[str, set[str]] = {}
        for violation in violations:
            final_warnings.append(violation)
            reason = _reason_for_validation_violation(violation)
            for task_id in _task_ids_from_validation_violation(violation):
                remove_by_task.setdefault(task_id, set()).add(reason)

        if not remove_by_task:
            return final_proposals, final_unschedulable, final_warnings

        final_proposals = [
            proposal for proposal in final_proposals if proposal.task_id not in remove_by_task
        ]
        for task_id, reasons in sorted(remove_by_task.items()):
            if task_id in already_unschedulable:
                continue
            final_unschedulable.append(
                UnschedulableTask(task_id=task_id, reasons=sorted(reasons))
            )
            already_unschedulable.add(task_id)


async def run_schedule(
    snapshot: ProjectSnapshot,
    priority: PriorityResponse,
    now: datetime,
    horizon_days: int = 14,
    use_llm: bool = True,
) -> ScheduleResponse:
    _apply_priority_assignments(snapshot, priority)
    priority_by_task = {item.task_id: item.score for item in priority.tasks_priority}

    ordered = priority_aware_topo_sort(
        [t for t in snapshot.tasks if t.status not in (TaskStatus.done, TaskStatus.cancelled)],
        priority_by_task,
    )

    virtual_events = list(snapshot.calendar_events)
    proposals: list[SlotProposal] = []
    unschedulable: list[UnschedulableTask] = []
    horizon_end = now + timedelta(days=horizon_days)
    end_by_task: dict[str, datetime] = {}
    task_by_id = {t.task_id: t for t in snapshot.tasks}

    for task in ordered:
        reasons: list[str] = []
        if task.estimated_hours is None:
            reasons.append("estimated_hours_missing")
        if task.assignee_id is None:
            reasons.append("assignee_missing")
        missing_scheduled_predecessors = [
            pid
            for pid in task.predecessor_ids
            if pid in task_by_id
            and task_by_id[pid].status not in (TaskStatus.done, TaskStatus.cancelled)
            and pid not in end_by_task
        ]
        if missing_scheduled_predecessors:
            reasons.append("predecessor_incomplete")
        if reasons:
            unschedulable.append(UnschedulableTask(task_id=task.task_id, reasons=reasons))
            continue

        earliest = now
        for pid in task.predecessor_ids:
            if pid in end_by_task:
                earliest = max(earliest, end_by_task[pid])

        candidates = _candidates_for_task(
            snapshot=snapshot,
            task=task,
            earliest=earliest,
            events=virtual_events,
            horizon_end=horizon_end,
        )
        if not candidates:
            unschedulable.append(
                UnschedulableTask(task_id=task.task_id, reasons=["no_capacity_before_deadline"])
            )
            continue

        candidates.sort(key=lambda c: (-c.fit_score, c.starts_at.isoformat()))
        selected = candidates[0]

        proposals.append(
            SlotProposal(
                task_id=task.task_id,
                candidate_slots=candidates,
                selected_index=0,
                rerank_rationale=None,
                rerank_source="deterministic",
            )
        )

        for block in _slot_blocks(selected):
            virtual_events.append(
                InternalCalendarEvent(
                    event_id=f"evt_virtual{len(virtual_events):02d}",
                    project_id=snapshot.project.project_id,
                    task_id=task.task_id,
                    assignee_id=task.assignee_id,
                    starts_at=block.starts_at,
                    ends_at=block.ends_at,
                    approved=True,
                    approved_at=None,
                    source="ai_suggested",
                )
            )
        end_by_task[task.task_id] = _slot_blocks(selected)[-1].ends_at

    proposals, repair_warnings = repair_schedule(snapshot=snapshot, proposals=proposals)
    proposals, unschedulable, repair_warnings = finalize_valid_schedule(
        snapshot=snapshot,
        proposals=proposals,
        unschedulable=unschedulable,
        warnings=repair_warnings,
    )
    if use_llm:
        proposals, rerank_warnings, rerank_calls = await _apply_llm_rerank(snapshot, priority, proposals)
    else:
        rerank_warnings, rerank_calls = [], 0

    response = ScheduleResponse(
        project_id=snapshot.project.project_id,
        slot_proposals=proposals,
        unschedulable=unschedulable,
        warnings=[*repair_warnings, *rerank_warnings],
    )
    object.__setattr__(response, "_agent_meta", {"rerank_calls": rerank_calls})
    return response


def has_hard_overlap(
    *,
    task: Task,
    starts_at: datetime,
    ends_at: datetime,
    calendar_events: list[InternalCalendarEvent],
) -> bool:
    return any(
        c.kind == "hard_overlap"
        for c in detect_conflicts(
            task=task, starts_at=starts_at, ends_at=ends_at, events=calendar_events
        )
    )


# ============================================================
# LLM Reranker
# ============================================================

def _should_rerank(proposals: list[SlotProposal]) -> bool:
    if not proposals:
        return False
    if all(len(p.candidate_slots) <= 1 for p in proposals):
        return False
    return True


def verify_rerank(
    original: list[SlotProposal], reranked_payload: dict | None
) -> list[str]:
    """위반 시 'rerank_violation:{task_id}' 단일 형식."""
    violations: list[str] = []

    if not reranked_payload or not isinstance(reranked_payload.get("rerankings"), list):
        violations.append("schedule_rerank_fallback")
        return violations

    rerankings = reranked_payload["rerankings"]
    if len(rerankings) != len(original):
        for proposal in original:
            violations.append(f"rerank_violation:{proposal.task_id}")
        return violations

    rerank_by_task = {
        resolved_task_id: item
        for item in rerankings
        if isinstance(item, dict)
        for resolved_task_id in [_resolve_rerank_task_id(original, item)]
        if resolved_task_id is not None
    }
    expected_task_ids = {proposal.task_id for proposal in original}
    supplied_task_ids = [
        resolved_task_id
        for item in rerankings
        if isinstance(item, dict)
        for resolved_task_id in [_resolve_rerank_task_id(original, item)]
        if resolved_task_id is not None
    ]
    if len(supplied_task_ids) != len(rerankings):
        for proposal in original:
            violations.append(f"rerank_violation:{proposal.task_id}")
        return violations
    if len(supplied_task_ids) != len(set(supplied_task_ids)):
        for proposal in original:
            violations.append(f"rerank_violation:{proposal.task_id}")
        return violations
    if any(task_id not in expected_task_ids for task_id in supplied_task_ids):
        for proposal in original:
            if proposal.task_id not in supplied_task_ids:
                violations.append(f"rerank_violation:{proposal.task_id}")
        if not violations and original:
            violations.append(f"rerank_violation:{original[0].task_id}")
        return violations

    for proposal in original:
        rerank = rerank_by_task.get(proposal.task_id)
        if not rerank:
            violations.append(f"rerank_violation:{proposal.task_id}")
            continue

        selected_index = rerank.get("selected_index")
        ranked_indices = rerank.get("ranked_indices")
        rationale = rerank.get("rationale")
        expected_indices = list(range(len(proposal.candidate_slots)))

        violated = False
        if not isinstance(selected_index, int) or selected_index not in expected_indices:
            violated = True
        elif not isinstance(ranked_indices, list) or sorted(ranked_indices) != expected_indices:
            violated = True
        elif selected_index != ranked_indices[0]:
            violated = True
        elif isinstance(rationale, str) and _has_forbidden_words(rationale):
            violated = True

        if violated:
            violations.append(f"rerank_violation:{proposal.task_id}")

    return violations


async def _apply_llm_rerank(
    snapshot: ProjectSnapshot,
    priority: PriorityResponse,
    proposals: list[SlotProposal],
) -> tuple[list[SlotProposal], list[str], int]:
    if not proposals or not llm_client.configured:
        return proposals, [], 0
    if not _should_rerank(proposals):
        return proposals, [], 0

    task_by_id = {task.task_id: task for task in snapshot.tasks}
    priority_by_id = {item.task_id: item for item in priority.tasks_priority}
    user_payload = json.dumps(
        {
            "project_goal": snapshot.project.goal,
            "tasks": [
                {
                    "task_index": task_index,
                    "task_id": p.task_id,
                    "title": task_by_id[p.task_id].title if p.task_id in task_by_id else p.task_id,
                    "description": task_by_id[p.task_id].description if p.task_id in task_by_id else "",
                    "priority_score": priority_by_id[p.task_id].score if p.task_id in priority_by_id else None,
                    "priority_rank": priority_by_id[p.task_id].rank if p.task_id in priority_by_id else None,
                    "candidates": [
                        {
                            "index": i,
                            "starts_at": s.starts_at.isoformat(),
                            "ends_at": s.ends_at.isoformat(),
                            "fit_score": s.fit_score,
                            "quality": s.quality.value,
                        }
                        for i, s in enumerate(p.candidate_slots)
                    ],
                }
                for task_index, p in enumerate(proposals)
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    calls = 0
    last_warnings: list[str] = []
    for _attempt in range(2):
        record_llm_call("schedule_rerank")
        calls += 1
        try:
            payload = await llm_client.chat_json(
                system=(
                    "You rerank safe schedule candidates. Output JSON only: "
                    "{\"rerankings\":[{\"task_index\":0,\"task_id\":\"...\",\"ranked_indices\":[0,1,2],"
                    "\"selected_index\":0,\"rationale\":\"...\"}]}. "
                    "Return exactly one reranking for every supplied task_index and copy task_id exactly. "
                    "task_index is the stable identifier for matching; use the supplied zero-based task_index. "
                    "For each task, ranked_indices must contain every candidate index exactly once. "
                    "Do not omit candidate indices, duplicate indices, or include indices not supplied. "
                    "selected_index must be one of ranked_indices and must be the first preferred index. "
                    "rationale must be Korean and <=120 chars. Do not invent or modify slots. Do not judge people."
                ),
                user=user_payload,
                purpose="schedule_rerank",
                temperature=0,
                max_tokens=900,
            )
        except TimeoutError:
            warnings = ["schedule_rerank_timeout"]
            record_llm_schema_result("schedule_rerank", False)
            record_llm_safety_result("schedule_rerank", False, warnings[0])
            last_warnings = warnings
            continue

        violations = verify_rerank(proposals, payload)
        if not violations:
            updated = _apply_verified_rerank(proposals, payload)
            global_violations = validate_selected_schedule(snapshot=snapshot, proposals=updated)
            if global_violations:
                record_llm_schema_result("schedule_rerank", False)
                record_llm_safety_result("schedule_rerank", False, global_violations[0])
                last_warnings = [f"rerank_violation:{proposal.task_id}" for proposal in proposals]
                continue
            record_llm_schema_result("schedule_rerank", True)
            record_llm_safety_result("schedule_rerank", True)
            return updated, [], calls

        record_llm_schema_result("schedule_rerank", False)
        record_llm_safety_result("schedule_rerank", False, violations[0])
        last_warnings = violations

    return proposals, last_warnings, calls


def _apply_verified_rerank(
    proposals: list[SlotProposal], payload: dict
) -> list[SlotProposal]:
    rerank_by_task = {
        resolved_task_id: item
        for item in payload.get("rerankings", [])
        if isinstance(item, dict)
        for resolved_task_id in [_resolve_rerank_task_id(proposals, item)]
        if resolved_task_id is not None
    }
    updated: list[SlotProposal] = []
    for p in proposals:
        rerank = rerank_by_task.get(p.task_id)
        if not rerank:
            updated.append(p)
            continue
        selected_index = _resolved_selected_index(p, rerank)
        if selected_index is None:
            updated.append(p)
            continue
        rationale = rerank.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            rationale = "AI가 후보 슬롯 순서를 조정했습니다."
        rationale = rationale.strip()[:120]
        updated.append(
            p.model_copy(
                update={
                    "selected_index": selected_index,
                    "rerank_rationale": rationale,
                    "rerank_source": "llm_reranked",
                }
            )
        )
    return updated


def _resolve_rerank_task_id(proposals: list[SlotProposal], item: dict) -> str | None:
    task_index = item.get("task_index")
    if isinstance(task_index, int) and 0 <= task_index < len(proposals):
        return proposals[task_index].task_id
    task_id = item.get("task_id")
    if isinstance(task_id, str) and any(proposal.task_id == task_id for proposal in proposals):
        return task_id
    return None


def _resolved_selected_index(proposal: SlotProposal, item: dict) -> int | None:
    candidate_count = len(proposal.candidate_slots)
    selected_index = item.get("selected_index")
    if "selected_index" in item:
        if isinstance(selected_index, int) and 0 <= selected_index < candidate_count:
            return selected_index
        return None
    ranked_indices = item.get("ranked_indices")
    if isinstance(ranked_indices, list):
        for index in ranked_indices:
            if isinstance(index, int) and 0 <= index < candidate_count:
                return index
    return None


# ============================================================
# LangGraph sub-graph
# ============================================================

class _SequentialScheduleGraph:
    async def ainvoke(self, state: dict):
        return {
            "schedule": await run_schedule(
                state["snapshot"],
                state["priority"],
                state["now"],
                state.get("horizon_days", 14),
                state.get("use_llm", True),
            )
        }


def _build_schedule_subgraph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ModuleNotFoundError:
        return _SequentialScheduleGraph()

    async def run_node(state: dict):
        return await _SequentialScheduleGraph().ainvoke(state)

    graph = StateGraph(dict)
    graph.add_node("run_schedule", run_node)
    graph.add_edge(START, "run_schedule")
    graph.add_edge("run_schedule", END)
    return graph.compile()


schedule_subgraph = _build_schedule_subgraph()
