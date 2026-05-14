from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta
from statistics import pstdev

from app.agents.common import find_cycle, hours_between
from app.schemas import (
    MemberWorkload,
    PriorityResponse,
    ProjectSnapshot,
    RiskCheck,
    RiskLevel,
    RiskResponse,
    RiskSuggestion,
    ScheduleResponse,
    SoftCheck,
    TaskRiskLevel,
    TaskStatus,
)
from app.services.llm_client import llm_client
from app.services.metrics import record_llm_call, record_llm_safety_result, record_llm_schema_result, record_policy_violation


CHECK_DEFS = [
    ("deadline_feasibility", "deadline", "마감일까지 완료 가능성", True),
    ("dependency_correctness", "dependency", "선후행 관계 오류", True),
    ("workload_concentration", "workload", "담당자 업무 쏠림", False),
]


def _priority_map(priority: PriorityResponse) -> dict[str, int]:
    return {item.task_id: item.score for item in priority.tasks_priority}


FORBIDDEN_WORDS = ("매력", "호감", "인상", "성격", "잘생", "멋지", "게으", "느려", "의지", "무능", "책임감", "능력")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
RISK_NARRATOR_SUMMARY_MAX_CHARS = 400
NO_DETERMINISTIC_BLOCKER_HINTS = ("없", "아니", "않", "no deterministic blocker", "no blocker")


def _has_forbidden_words(text: str) -> bool:
    found = any(word in text for word in FORBIDDEN_WORDS)
    if found:
        record_policy_violation("forbidden_word")
    return found


def _number_tokens(text: str) -> set[str]:
    tokens = set()
    for value in NUMBER_RE.findall(text):
        tokens.add(value)
        try:
            tokens.add(f"{float(value):g}")
        except ValueError:
            pass
    return tokens


def _uses_only_allowed_numbers(text: str, allowed_text: str) -> bool:
    used = _number_tokens(text)
    if not used:
        return True
    allowed = _number_tokens(allowed_text)
    ok = used.issubset(allowed)
    if not ok:
        record_policy_violation("invented_number")
    return ok


def _respects_failed_check_contract(text: str, failed_checks: list[RiskCheck]) -> bool:
    if failed_checks:
        return True
    lowered = text.lower()
    ok = any(hint in lowered for hint in NO_DETERMINISTIC_BLOCKER_HINTS)
    if not ok:
        record_policy_violation("invented_risk")
    return ok


def _avoids_raw_check_ids(text: str, failed_checks: list[RiskCheck]) -> bool:
    raw_ids_with_labels = [check.id for check in failed_checks if check.label and check.id in text]
    ok = not raw_ids_with_labels
    if not ok:
        record_policy_violation("raw_check_id")
    return ok


def _schedule_hours(snapshot: ProjectSnapshot, schedule: ScheduleResponse | None, now: datetime, member_id: str) -> float:
    if schedule is None:
        return 0
    task_by_id = {task.task_id: task for task in snapshot.tasks}
    horizon = now + timedelta(days=7)
    total = 0.0
    for proposal in schedule.slot_proposals:
        task = task_by_id.get(proposal.task_id)
        if task is None or task.assignee_id != member_id:
            continue
        slot = proposal.candidate_slots[proposal.selected_index]
        if slot.starts_at >= horizon:
            continue
        total += hours_between(slot.starts_at, slot.ends_at)
    return total


def _workloads(snapshot: ProjectSnapshot, schedule: ScheduleResponse | None, now: datetime) -> list[MemberWorkload]:
    items: list[MemberWorkload] = []
    for member in snapshot.members:
        scheduled = _schedule_hours(snapshot, schedule, now, member.member_id)
        capacity = member.weekly_capacity_hours or 40
        utilization = round(scheduled / capacity, 2) if capacity else 0
        items.append(
            MemberWorkload(
                member_id=member.member_id,
                scheduled_hours_next_7d=round(scheduled, 2),
                capacity_hours=capacity,
                utilization=utilization,
                is_overloaded=utilization > 1,
            )
        )
    return items


def _task_risks(snapshot: ProjectSnapshot, priority: PriorityResponse, now: datetime) -> list[TaskRiskLevel]:
    scores = _priority_map(priority)
    risks: list[TaskRiskLevel] = []
    for task in snapshot.tasks:
        score = scores.get(task.task_id, 0)
        reasons: list[str] = []
        if task.deadline and task.deadline < now and task.status not in (TaskStatus.done, TaskStatus.cancelled):
            level = RiskLevel.overdue
            reasons.append("마감일이 지났습니다.")
        elif score >= 80 and task.progress_percent < 30:
            level = RiskLevel.at_risk
            reasons.append("우선순위가 높고 진척률이 낮습니다.")
        elif score >= 60:
            level = RiskLevel.watch
            reasons.append("우선순위가 높아 관찰이 필요합니다.")
        else:
            level = RiskLevel.ok
            reasons.append("현재 결정적 위험 신호가 낮습니다.")
        risks.append(TaskRiskLevel(task_id=task.task_id, level=level, reasons=reasons))
    return risks


def _evaluate_checks(
    snapshot: ProjectSnapshot,
    priority: PriorityResponse,
    schedule: ScheduleResponse | None,
    workloads: list[MemberWorkload],
    risks: list[TaskRiskLevel],
    now: datetime,
) -> list[RiskCheck]:
    task_by_id = {task.task_id: task for task in snapshot.tasks}
    utilization_values = [item.utilization for item in workloads]
    results: dict[str, tuple[str, bool, list[str]]] = {}

    active_tasks = [task for task in snapshot.tasks if task.status not in (TaskStatus.done, TaskStatus.cancelled)]
    remaining_hours = sum(task.estimated_hours or 0 for task in active_tasks)
    days_left = max(0, (snapshot.project.ends_at - now.date()).days)
    project_capacity_hours = days_left * 8
    overdue_tasks = [task.task_id for task in active_tasks if task.deadline and task.deadline < now]
    no_capacity_tasks = [
        item.task_id
        for item in (schedule.unschedulable if schedule else [])
        if "no_capacity_before_deadline" in item.reasons
    ]
    deadline_facts = [
        f"마감 지난 Task {len(overdue_tasks)}건",
        f"마감 전 배치 불가 Task {len(no_capacity_tasks)}건",
        f"남은 추정 {remaining_hours}h / 남은 가능 약 {project_capacity_hours}h",
    ]
    deadline_failed = bool(overdue_tasks or no_capacity_tasks or remaining_hours > project_capacity_hours)
    results["deadline_feasibility"] = (
        "pass" if not deadline_failed else "fail",
        True,
        deadline_facts,
    )

    cycle = find_cycle(snapshot.tasks)
    predecessor_deadline_ok = True
    predecessor_deadline_facts: list[str] = []
    for task in snapshot.tasks:
        for pred_id in task.predecessor_ids:
            pred = task_by_id.get(pred_id)
            if pred and pred.deadline and task.deadline and pred.deadline > task.deadline:
                predecessor_deadline_ok = False
                predecessor_deadline_facts.append(f"{pred_id} 마감 {pred.deadline.isoformat()} > {task.task_id} 마감 {task.deadline.isoformat()}")
    schedule_slot_by_task = {}
    if schedule:
        for proposal in schedule.slot_proposals:
            schedule_slot_by_task[proposal.task_id] = proposal.candidate_slots[proposal.selected_index]
    predecessor_slot_ok = True
    predecessor_slot_facts: list[str] = []
    for task in snapshot.tasks:
        slot = schedule_slot_by_task.get(task.task_id)
        if slot is None:
            continue
        for pred_id in task.predecessor_ids:
            pred_slot = schedule_slot_by_task.get(pred_id)
            if pred_slot and pred_slot.ends_at > slot.starts_at:
                predecessor_slot_ok = False
                predecessor_slot_facts.append(f"{pred_id} 종료 {pred_slot.ends_at.isoformat()} > {task.task_id} 시작 {slot.starts_at.isoformat()}")
    predecessor_incomplete_tasks = [
        item.task_id
        for item in (schedule.unschedulable if schedule else [])
        if "predecessor_incomplete" in item.reasons
    ]
    dependency_failed = (
        cycle is not None
        or bool(predecessor_incomplete_tasks)
        or not predecessor_deadline_ok
        or (schedule is not None and not predecessor_slot_ok)
    )
    dependency_facts = []
    if cycle:
        dependency_facts.append(f"순환 경로: {' -> '.join(cycle)}")
    dependency_facts.extend(predecessor_deadline_facts[:3])
    dependency_facts.extend(predecessor_slot_facts[:3])
    dependency_facts.extend([f"선행 미완료로 배치 불가: {task_id}" for task_id in predecessor_incomplete_tasks[:3]])
    if not dependency_facts:
        dependency_facts.append("순환, 마감 순서, 일정 순서를 확인했습니다.")
    results["dependency_correctness"] = (
        "pass" if not dependency_failed else "fail",
        True,
        dependency_facts,
    )

    utilization_stddev = pstdev(utilization_values) if len(utilization_values) >= 2 else 0
    total_scheduled = sum(item.scheduled_hours_next_7d for item in workloads)
    max_workload = max(workloads, key=lambda item: item.scheduled_hours_next_7d, default=None)
    max_share = (max_workload.scheduled_hours_next_7d / total_scheduled) if max_workload and total_scheduled > 0 else 0
    has_overloaded_member = any(item.is_overloaded for item in workloads)
    workload_failed = has_overloaded_member or utilization_stddev > 0.4 or (len(workloads) >= 2 and max_share >= 0.85 and total_scheduled > 0)
    workload_facts = [
        f"최대 utilization {max(utilization_values, default=0):.2f}",
        f"utilization 표준편차 {utilization_stddev:.2f}",
        f"최대 담당자 배정 비중 {max_share:.2f}",
    ]
    results["workload_concentration"] = (
        "pass" if not workload_failed else "fail",
        schedule is not None,
        workload_facts,
    )

    checks: list[RiskCheck] = []
    for check_id, group, label, is_blocker in CHECK_DEFS:
        result, applicable, facts = results[check_id]
        checks.append(
            RiskCheck(
                id=check_id,
                group=group,
                label=label,
                result=result if applicable else "not_applicable",
                applicable=applicable,
                is_blocker=is_blocker,
                evidence_facts=facts,
            )
        )
    return checks


def _least_loaded_member_id(snapshot: ProjectSnapshot, workloads: list[MemberWorkload]) -> str | None:
    if not snapshot.members:
        return None
    workload_by_member = {item.member_id: item.utilization for item in workloads}
    active_task_count_by_member = {
        member.member_id: sum(
            1
            for task in snapshot.tasks
            if task.assignee_id == member.member_id and task.status in (TaskStatus.todo, TaskStatus.in_progress)
        )
        for member in snapshot.members
    }
    return min(
        snapshot.members,
        key=lambda item: (
            workload_by_member.get(item.member_id, 0),
            active_task_count_by_member.get(item.member_id, 0),
            item.member_id,
        ),
    ).member_id


def _most_overloaded_member_id(workloads: list[MemberWorkload]) -> str | None:
    if not workloads:
        return None
    return max(workloads, key=lambda item: (item.utilization, item.scheduled_hours_next_7d, item.member_id)).member_id


def _lowest_priority_active_task_for_member(
    *,
    snapshot: ProjectSnapshot,
    priority: PriorityResponse,
    member_id: str,
) -> str | None:
    priority_by_task = _priority_map(priority)
    active = [
        task
        for task in snapshot.tasks
        if task.assignee_id == member_id and task.status in (TaskStatus.todo, TaskStatus.in_progress)
    ]
    if not active:
        return None
    return min(active, key=lambda task: (priority_by_task.get(task.task_id, 0), task.deadline or datetime.max, task.task_id)).task_id


def _member_label(snapshot: ProjectSnapshot, member_id: str | None) -> str | None:
    if not member_id or member_id == "(미정)":
        return None
    member = next((item for item in snapshot.members if item.member_id == member_id), None)
    if member is None:
        return member_id
    return f"{member.name}({member.role})" if member.role else member.name


def _suggestion_id(check_id: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]", "", check_id)
    return f"rs_{compact[:24]}0000"


def _time_from_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _working_windows_for_day(
    snapshot: ProjectSnapshot,
    task_id: str,
    day: date,
    tzinfo,
) -> list[tuple[datetime, datetime]]:
    task = next((item for item in snapshot.tasks if item.task_id == task_id), None)
    member = next((item for item in snapshot.members if task and item.member_id == task.assignee_id), None)
    if member:
        member_windows = sorted(
            (item for item in member.available_hours if item.day_of_week == day.weekday()),
            key=lambda item: item.start,
        )
        if member_windows:
            return [
                (
                    datetime.combine(day, _time_from_hhmm(item.start), tzinfo=tzinfo),
                    datetime.combine(day, _time_from_hhmm(item.end), tzinfo=tzinfo),
                )
                for item in member_windows
            ]
        if member.available_hours:
            return []
    hour_range = snapshot.project.default_working_hours.weekend if day.weekday() >= 5 else snapshot.project.default_working_hours.weekday
    if not hour_range.enabled:
        return []
    return [
        (
            datetime.combine(day, _time_from_hhmm(hour_range.start), tzinfo=tzinfo),
            datetime.combine(day, _time_from_hhmm(hour_range.end), tzinfo=tzinfo),
        )
    ]


def _free_intervals_after_events(
    intervals: list[tuple[datetime, datetime]],
    busy_intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    free_intervals = intervals
    for busy_start, busy_end in busy_intervals:
        next_free: list[tuple[datetime, datetime]] = []
        for free_start, free_end in free_intervals:
            if busy_end <= free_start or busy_start >= free_end:
                next_free.append((free_start, free_end))
                continue
            if free_start < busy_start:
                next_free.append((free_start, min(busy_start, free_end)))
            if busy_end < free_end:
                next_free.append((max(busy_end, free_start), free_end))
        free_intervals = next_free
    return [(start, end) for start, end in free_intervals if end > start]


def _suggested_deadline_for_task(snapshot: ProjectSnapshot, task, now: datetime) -> str | None:
    if task.deadline is None or task.estimated_hours is None:
        return None
    remaining_hours = float(task.estimated_hours)
    cumulative_free_hours = 0.0
    for offset in range(180):
        day = now.date() + timedelta(days=offset)
        windows = _working_windows_for_day(snapshot, task.task_id, day, now.tzinfo)
        if not windows:
            continue
        busy = [
            (event.starts_at, event.ends_at)
            for event in snapshot.calendar_events
            if event.assignee_id == task.assignee_id
            and event.starts_at.date() == day
            and (event.approved or event.source == "external_blocking")
        ]
        free_intervals = _free_intervals_after_events(windows, busy)
        if offset == 0:
            free_intervals = [(max(start, now), end) for start, end in free_intervals if end > now]
        if not free_intervals:
            continue
        day_free_hours = sum(hours_between(start, end) for start, end in free_intervals)
        largest_free_hours = max(hours_between(start, end) for start, end in free_intervals)
        cumulative_free_hours += day_free_hours
        if largest_free_hours >= remaining_hours or cumulative_free_hours >= remaining_hours:
            return max(end for _, end in free_intervals).isoformat()
    return None


def _deadline_action_context(
    *,
    snapshot: ProjectSnapshot,
    priority: PriorityResponse,
    schedule: ScheduleResponse | None,
    now: datetime,
) -> tuple[dict | None, list[str], str | None]:
    if schedule is None:
        return None, [], None
    task_by_id = {task.task_id: task for task in snapshot.tasks}
    unschedulable_by_task = {item.task_id: item for item in schedule.unschedulable}
    for priority_item in sorted(priority.tasks_priority, key=lambda item: item.rank)[:5]:
        unscheduled = unschedulable_by_task.get(priority_item.task_id)
        task = task_by_id.get(priority_item.task_id)
        if unscheduled is None or task is None:
            continue
        task_title = task.title or task.task_id
        reasons = list(unscheduled.reasons)
        if "assignee_missing" in reasons:
            return (
                {"type": "reassign", "target_task_id": task.task_id},
                [f"미배치 원인: {task_title} 담당자 미지정"],
                f"AI 제안: '{task_title}' 담당자를 지정한 뒤 다시 분석하세요.",
            )
        if "estimated_hours_missing" in reasons:
            return (
                {"type": "split_task", "target_task_id": task.task_id},
                [f"미배치 원인: {task_title} 예상 시간 누락"],
                f"AI 제안: '{task_title}' 예상 시간을 입력한 뒤 다시 분석하세요.",
            )
        if "predecessor_incomplete" in reasons:
            blocking_titles = [
                task_by_id[pred_id].title
                for pred_id in task.predecessor_ids
                if pred_id in task_by_id
                and task_by_id[pred_id].status not in (TaskStatus.done, TaskStatus.cancelled)
            ]
            blocking_text = ", ".join(blocking_titles[:2]) if blocking_titles else "선행 Task"
            predecessor_id = next(
                (
                    pred_id
                    for pred_id in task.predecessor_ids
                    if pred_id in task_by_id
                    and task_by_id[pred_id].status not in (TaskStatus.done, TaskStatus.cancelled)
                ),
                None,
            )
            return (
                {"type": "remove_predecessor", "target_task_id": task.task_id, "to": predecessor_id}
                if predecessor_id
                else {"type": "reschedule", "target_task_id": task.task_id},
                [f"미배치 원인: {task_title} 선행 미완료", f"막는 Task: {blocking_text}"],
                f"AI 조치: '{task_title}'의 선행 관계에서 '{blocking_text}'를 제거하는 변경안을 적용합니다.",
            )
        if "no_capacity_before_deadline" in reasons:
            suggested_deadline = _suggested_deadline_for_task(snapshot, task, now)
            action = {
                "type": "reschedule",
                "target_task_id": task.task_id,
                "from": task.deadline.isoformat() if task.deadline else None,
                "to": suggested_deadline,
            }
            date_hint = f" 새 마감 후보는 {suggested_deadline[:10]}입니다." if suggested_deadline else ""
            return (
                action,
                [f"미배치 원인: {task_title} 마감 전 가용 슬롯 없음"],
                f"AI 조치: '{task_title}' 마감일을 {suggested_deadline[:10]}로 변경해 다시 배치 가능하게 합니다."
                if suggested_deadline
                else f"AI 제안: '{task_title}'을 더 작은 작업으로 쪼개거나 마감일을 늦추거나 예상 시간을 줄이고, 담당자를 조정하거나 가용 시간을 추가한 뒤 다시 분석하세요.{date_hint}",
            )
        if "deadline_in_past" in reasons:
            return (
                {"type": "reschedule", "target_task_id": task.task_id},
                [f"미배치 원인: {task_title} 마감일 경과"],
                f"AI 제안: '{task_title}' 마감일을 현실적인 날짜로 다시 잡거나 이미 끝난 작업이면 완료 처리한 뒤 다시 분석하세요.",
            )
        return (
            {"type": "reschedule", "target_task_id": task.task_id},
            [f"미배치 원인: {task_title} {', '.join(reasons)}"],
            f"AI 제안: '{task_title}'의 미배치 원인을 수정한 뒤 다시 분석하세요.",
        )
    return None, [], None


def _dependency_action_context(
    *,
    snapshot: ProjectSnapshot,
    schedule: ScheduleResponse | None,
) -> tuple[dict | None, list[str], str | None]:
    task_by_id = {task.task_id: task for task in snapshot.tasks}
    cycle = find_cycle(snapshot.tasks)
    if cycle and len(cycle) >= 2:
        target_task_id = cycle[0]
        predecessor_id = cycle[1]
        target_task = task_by_id.get(target_task_id)
        predecessor = task_by_id.get(predecessor_id)
        target_title = target_task.title if target_task else target_task_id
        predecessor_title = predecessor.title if predecessor else predecessor_id
        return (
            {"type": "remove_predecessor", "target_task_id": target_task_id, "to": predecessor_id},
            [f"순환 경로: {' -> '.join(cycle)}"],
            f"AI 조치: '{target_title}'에서 선행 Task '{predecessor_title}' 연결을 끊어 순환 선후행 관계를 해소합니다.",
        )
    if schedule:
        scheduled_task_ids = {proposal.task_id for proposal in schedule.slot_proposals}
        for item in schedule.unschedulable:
            if "predecessor_incomplete" not in item.reasons:
                continue
            task = task_by_id.get(item.task_id)
            if task is None:
                continue
            predecessor_id = next(
                (
                    pred_id
                    for pred_id in task.predecessor_ids
                    if pred_id in task_by_id
                    and task_by_id[pred_id].status not in (TaskStatus.done, TaskStatus.cancelled)
                    and pred_id not in scheduled_task_ids
                ),
                None,
            )
            if predecessor_id:
                predecessor = task_by_id[predecessor_id]
                return (
                    {"type": "remove_predecessor", "target_task_id": task.task_id, "to": predecessor_id},
                    [f"선행 Task '{predecessor.title}' 미완료로 '{task.title}' 배치 불가"],
                    f"AI 조치: '{task.title}'에서 선행 Task '{predecessor.title}' 연결을 제거해 배치 가능 여부를 다시 확인합니다.",
                )
    for task in snapshot.tasks:
        for pred_id in task.predecessor_ids:
            pred = task_by_id.get(pred_id)
            if pred and pred.deadline and task.deadline and pred.deadline > task.deadline:
                return (
                    {"type": "reschedule", "target_task_id": task.task_id},
                    [f"선행 Task '{pred.title}' 마감이 후행 Task '{task.title}'보다 늦습니다."],
                    f"AI 제안: '{task.title}' 마감이 선행 Task '{pred.title}' 마감 이후가 되도록 마감 순서를 조정하세요.",
                )
    if schedule:
        slot_by_task = {
            proposal.task_id: proposal.candidate_slots[proposal.selected_index]
            for proposal in schedule.slot_proposals
        }
        for task in snapshot.tasks:
            slot = slot_by_task.get(task.task_id)
            if slot is None:
                continue
            for pred_id in task.predecessor_ids:
                pred_slot = slot_by_task.get(pred_id)
                pred = task_by_id.get(pred_id)
                if pred_slot and pred_slot.ends_at > slot.starts_at:
                    pred_title = pred.title if pred else pred_id
                    return (
                        {"type": "reschedule", "target_task_id": task.task_id},
                        [f"선행 Task '{pred_title}' 종료가 후행 Task '{task.title}' 시작보다 늦습니다."],
                        f"AI 제안: '{task.title}'보다 '{pred_title}'이 먼저 끝나도록 일정을 조정하거나 선후행 관계를 수정하세요.",
                    )
    return None, [], None


def _suggestions(
    checks: list[RiskCheck],
    snapshot: ProjectSnapshot,
    priority: PriorityResponse,
    schedule: ScheduleResponse | None,
    workloads: list[MemberWorkload],
    now: datetime,
) -> list[RiskSuggestion]:
    suggestions: list[RiskSuggestion] = []
    task_by_id = {task.task_id: task for task in snapshot.tasks}
    for check in [item for item in checks if item.applicable and item.result == "fail"][:5]:
        action = {"type": "reschedule" if check.group == "deadline" else "reassign"}
        rationale_facts = [*check.evidence_facts]
        user_facing_text = f"{check.label} 체크가 실패했습니다. 입력을 확인하거나 재분석하세요."
        if check.id == "deadline_feasibility":
            deadline_action, action_facts, action_text = _deadline_action_context(
                snapshot=snapshot,
                priority=priority,
                schedule=schedule,
                now=now,
            )
            if deadline_action and action_text:
                action = deadline_action
                rationale_facts.extend(action_facts)
                user_facing_text = action_text
        elif check.id == "dependency_correctness":
            dependency_action, action_facts, action_text = _dependency_action_context(
                snapshot=snapshot,
                schedule=schedule,
            )
            if dependency_action and action_text:
                action = dependency_action
                rationale_facts.extend(action_facts)
                user_facing_text = action_text
        elif check.id == "workload_concentration":
            source_member_id = _most_overloaded_member_id(workloads)
            target_member_id = _least_loaded_member_id(snapshot, workloads)
            target_task_id = (
                _lowest_priority_active_task_for_member(snapshot=snapshot, priority=priority, member_id=source_member_id)
                if source_member_id
                else None
            )
            if target_task_id and source_member_id and target_member_id and source_member_id != target_member_id:
                action = {"type": "reassign", "target_task_id": target_task_id, "from": source_member_id, "to": target_member_id}
                target_label = _member_label(snapshot, target_member_id)
                if target_label:
                    task_title = task_by_id.get(target_task_id).title if task_by_id.get(target_task_id) else target_task_id
                    rationale_facts.append(f"추천 담당자: {target_label}")
                    user_facing_text = f"부하 조정을 위해 '{task_title}' Task를 {target_label}에게 옮기는 안입니다."

        suggestions.append(
            RiskSuggestion(
                id=_suggestion_id(check.id),
                fixes_check_ids=[check.id],
                action=action,
                rationale_facts=rationale_facts,
                removes_blocker=check.is_blocker,
                user_facing_text=user_facing_text,
            )
        )
    return suggestions


def _valid_soft_check(item: dict, valid_task_ids: set[str]) -> SoftCheck | None:
    confidence = item.get("confidence")
    if not isinstance(confidence, int | float) or confidence < 0.5:
        record_llm_safety_result("risk_soft_checks", False, "low_confidence")
    involved_task_ids = item.get("involved_task_ids")
    has_hallucinated_ids = isinstance(involved_task_ids, list) and any(task_id not in valid_task_ids for task_id in involved_task_ids)
    if has_hallucinated_ids:
        record_llm_safety_result("risk_soft_checks", False, "hallucinated_task_id")
        record_policy_violation("hallucinated_task_id")
    try:
        check = SoftCheck(**item)
    except Exception:
        if not isinstance(confidence, int | float) or confidence >= 0.5:
            record_llm_safety_result("risk_soft_checks", False, "schema_invalid")
        record_llm_schema_result("risk_soft_checks", False)
        return None
    if any(task_id not in valid_task_ids for task_id in check.involved_task_ids):
        if not has_hallucinated_ids:
            record_llm_safety_result("risk_soft_checks", False, "hallucinated_task_id")
            record_policy_violation("hallucinated_task_id")
        record_llm_schema_result("risk_soft_checks", False)
        return None
    if _has_forbidden_words(check.user_facing_text):
        record_llm_safety_result("risk_soft_checks", False, "forbidden_word")
        record_llm_schema_result("risk_soft_checks", False)
        return None
    record_llm_safety_result("risk_soft_checks", True)
    record_llm_schema_result("risk_soft_checks", True)
    return check


async def _llm_soft_checks(snapshot: ProjectSnapshot) -> tuple[list[SoftCheck], bool]:
    if not llm_client.configured:
        return [], False
    record_llm_call("risk_soft_checks")
    try:
        payload = await llm_client.chat_json(
            system=(
                "You are a conservative project risk reviewer. "
                "Find soft project risks only when deterministic checks cannot catch them. "
                "Hard checks already handle deadline feasibility, explicit dependency correctness, and workload concentration. "
                "Do not report those as soft checks. "
                "Output JSON only in this exact shape: "
                "{\"soft_checks\":[{\"id\":\"S1\",\"trigger_label\":\"implicit_dependency_suspected\","
                "\"confidence\":0.7,\"involved_task_ids\":[\"task_id\"],"
                "\"supporting_facts\":[\"field-level fact from input\"],"
                "\"suggested_action\":null,\"user_facing_text\":\"Korean PM-facing sentence\"}]}. "
                "Allowed trigger_label values: implicit_dependency_suspected, repeated_delay_root_cause, "
                "milestone_task_mismatch, task_definition_too_vague, duplicate_task_suspected. "
                "Rules by trigger_label: "
                "task_definition_too_vague means a task title or description lacks a clear deliverable or completion condition; "
                "duplicate_task_suspected means two or more tasks have substantially overlapping titles or descriptions; "
                "implicit_dependency_suspected means task wording clearly implies an unstated order but predecessor_ids do not express it; "
                "repeated_delay_root_cause means the same delay_reason appears across two or more tasks; "
                "milestone_task_mismatch means a task clearly does not support any supplied milestone or conflicts with one. "
                "Only emit a soft check when at least one concrete supplied fact supports it. "
                "If the evidence is weak or the issue belongs to hard checks, return {\"soft_checks\":[]}. "
                "Return at most 3 soft_checks. "
                "confidence must be between 0.5 and 1.0. "
                "involved_task_ids must use existing task IDs exactly. "
                "suggested_action.type must be one of reschedule, reassign, split_task, raise_importance, "
                "lower_importance, add_predecessor, remove_predecessor, or suggested_action must be null. "
                "Use suggested_action null unless the action is obvious and can be expressed with existing IDs. "
                "Use only supplied task/member/milestone facts. "
                "Do not invent IDs, dates, numbers, progress, capacity, causes, or people assessments. "
                "Prefer fewer high-confidence checks over many weak checks, and do not judge people."
            ),
            user=json.dumps(
                {
                    "tasks": [
                        {
                            "task_id": task.task_id,
                            "title": task.title,
                            "description": task.description,
                            "delay_reason": task.delay_reason,
                            "predecessor_ids": task.predecessor_ids,
                        }
                        for task in snapshot.tasks
                    ],
                    "milestones": [item.model_dump(mode="json") for item in snapshot.milestones],
                    "members": [{"member_id": item.member_id, "role": item.role} for item in snapshot.members],
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            purpose="risk_soft_checks",
            temperature=0.2,
            max_tokens=1200,
        )
    except TimeoutError:
        record_llm_safety_result("risk_soft_checks", False, "timeout")
        record_llm_schema_result("risk_soft_checks", False)
        return [], True
    valid_task_ids = {task.task_id for task in snapshot.tasks}
    checks: list[SoftCheck] = []
    items = (payload or {}).get("soft_checks") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        record_llm_safety_result("risk_soft_checks", False, "schema_invalid")
        record_llm_schema_result("risk_soft_checks", False)
        return checks, False
    for item in items:
        if isinstance(item, dict):
            check = _valid_soft_check(item, valid_task_ids)
            if check:
                checks.append(check)
        else:
            record_llm_safety_result("risk_soft_checks", False, "schema_invalid")
            record_llm_schema_result("risk_soft_checks", False)
    return checks, False


async def _llm_narrate(
    *,
    checks: list[RiskCheck],
    risks: list[TaskRiskLevel],
    workloads: list[MemberWorkload],
    suggestions: list[RiskSuggestion],
    fallback_summary: str,
) -> tuple[str, int]:
    if not llm_client.configured:
        return fallback_summary, 0
    failed_checks = [check for check in checks if check.applicable and check.result == "fail"]
    user_payload = json.dumps(
        {
            "failed_checks": [check.model_dump(mode="json") for check in failed_checks],
            "task_risk_levels": [risk.model_dump(mode="json") for risk in risks],
            "member_workload": [workload.model_dump(mode="json") for workload in workloads],
            "suggestions": [suggestion.model_dump(mode="json", by_alias=True) for suggestion in suggestions],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    calls = 0
    for _ in range(2):
        record_llm_call("risk_narrate")
        payload = await llm_client.chat_json(
            system=(
                "You summarize deterministic project risk facts in Korean for a PM. "
                "Do not perform new risk analysis. Output JSON only in this exact shape: {\"summary\":\"...\"}. "
                "Use only supplied failed_checks, evidence_facts, task_risk_levels, member_workload, and suggestions. "
                "Prioritize failed_checks over task_risk_levels and member_workload. "
                "If failed_checks are present, mention the failed check label and the main PM action from suggestions; never expose raw check IDs. "
                "If failed_checks is empty, say there is no deterministic blocker and do not invent a new risk. "
                "Do not mention soft or speculative risks unless they are present in the supplied suggestions. "
                "Copy numeric tokens exactly from the supplied JSON if you use numbers, but prefer check labels and PM actions over numbers. "
                "Do not round, convert, estimate, invent numbers, invent task/member/check IDs, or judge people. "
                f"Keep summary <={RISK_NARRATOR_SUMMARY_MAX_CHARS} chars."
            ),
            user=user_payload,
            purpose="risk_narrate",
            temperature=0,
            max_tokens=700,
        )
        calls += 1
        summary = (payload or {}).get("summary")
        if (
            isinstance(summary, str)
            and summary.strip()
            and len(summary) <= RISK_NARRATOR_SUMMARY_MAX_CHARS
            and not _has_forbidden_words(summary)
            and _uses_only_allowed_numbers(summary, user_payload)
            and _respects_failed_check_contract(summary, failed_checks)
            and _avoids_raw_check_ids(summary, failed_checks)
        ):
            record_llm_schema_result("risk_narrate", True)
            return summary, calls
        record_llm_schema_result("risk_narrate", False)
    return fallback_summary, calls


def _fallback_soft_checks(snapshot: ProjectSnapshot):
    checks: list[SoftCheck] = []
    active = [task for task in snapshot.tasks if task.status not in (TaskStatus.done, TaskStatus.cancelled)]
    for task in active:
        if len(checks) >= 5:
            break
        if len(task.title.strip()) <= 8 and len(task.description.strip()) < 20:
            text = "Task 정의가 짧아 완료 조건을 PM이 확인해야 합니다."
            if _has_forbidden_words(text):
                continue
            checks.append(
                SoftCheck(
                    id="S4",
                    trigger_label="task_definition_too_vague",
                    confidence=0.72,
                    involved_task_ids=[task.task_id],
                    supporting_facts=[f"{task.task_id}.title='{task.title}'", "description 길이가 짧음"],
                    suggested_action=None,
                    user_facing_text=text,
                )
            )
    delay_reason_groups: dict[str, list[str]] = {}
    for task in active:
        if task.delay_reason:
            key = task.delay_reason.strip()[:24]
            delay_reason_groups.setdefault(key, []).append(task.task_id)
    for reason, task_ids in delay_reason_groups.items():
        if len(task_ids) < 2 or len(checks) >= 5:
            continue
        checks.append(
            SoftCheck(
                id="S2",
                trigger_label="repeated_delay_root_cause",
                confidence=0.66,
                involved_task_ids=task_ids[:5],
                supporting_facts=[f"delay_reason 반복: {reason}"],
                suggested_action=None,
                user_facing_text="여러 Task에서 같은 지연 사유가 반복되어 프로젝트 차원의 원인 확인이 필요합니다.",
            )
        )
    return checks


def _fallback_summary(failed_checks: list[RiskCheck], suggestions: list[RiskSuggestion]) -> str:
    failed_blocker_checks = [check for check in failed_checks if check.is_blocker]
    if not failed_blocker_checks:
        return "현재 결정적 blocker는 없습니다. 실패한 보조 체크가 있으면 제안 카드를 검토하세요."
    labels = ", ".join(check.label or check.id for check in failed_blocker_checks)
    deadline_check = next((check for check in failed_blocker_checks if check.id == "deadline_feasibility"), None)
    deadline_hint = ""
    if deadline_check:
        no_capacity_fact = next((fact for fact in deadline_check.evidence_facts if fact.startswith("마감 전 배치 불가 Task ")), "")
        overdue_fact = next((fact for fact in deadline_check.evidence_facts if fact.startswith("마감 지난 Task ")), "")
        if no_capacity_fact and " 0건" not in no_capacity_fact:
            deadline_hint = " 마감 전 자동 배치할 수 없는 Task가 있습니다."
        elif overdue_fact and " 0건" not in overdue_fact:
            deadline_hint = " 마감일이 지난 Task가 있습니다."
        else:
            deadline_hint = " 남은 작업량이 마감 전 가용 시간보다 큽니다."
    primary_action = next((item.user_facing_text for item in suggestions if item.removes_blocker), None)
    if primary_action:
        return f"{labels} 체크가 실패했습니다.{deadline_hint} {primary_action}"[:RISK_NARRATOR_SUMMARY_MAX_CHARS]
    return f"{labels} 체크가 실패했습니다.{deadline_hint} 승인 전 일정과 선후행 관계를 PM이 재검토하세요."


async def run_risk(
    snapshot: ProjectSnapshot,
    priority: PriorityResponse,
    schedule: ScheduleResponse | None,
    now: datetime,
    use_llm: bool = True,
    prefetched_soft_checks: list[SoftCheck] | None = None,
    prefetched_soft_checks_timeout: bool = False,
    prefetched_soft_check_calls: int | None = None,
) -> RiskResponse:
    # 이번 실행에서 LLM 경로를 실제로 쓸 수 있는지 판단해 meta 호출 수 계산에 사용합니다.
    llm_configured = use_llm and llm_client.configured
    # 우선순위 점수와 현재 시각을 기준으로 task별 위험 등급을 먼저 계산합니다.
    risks = _task_risks(snapshot, priority, now)
    # schedule 제안이 있으면 담당자별 7일 배정량과 과부하 여부를 계산합니다.
    workloads = _workloads(snapshot, schedule, now)
    # deadline, dependency, workload의 3개 hard check를 결정적으로 평가합니다.
    checks = _evaluate_checks(snapshot, priority, schedule, workloads, risks, now)
    failed_checks = [check for check in checks if check.applicable and check.result == "fail"]
    # 실패한 hard check 중 승인 전에 반드시 봐야 하는 blocker check id만 모읍니다.
    blockers_failed = [check.id for check in failed_checks if check.is_blocker]
    # 실패한 check를 PM이 실행할 수 있는 reschedule/reassign 같은 조치 제안으로 변환합니다.
    suggestions = _suggestions(checks, snapshot, priority, schedule, workloads, now)
    # orchestrator가 미리 실행한 soft check timeout 여부를 그대로 이어받습니다.
    soft_checks_timeout = prefetched_soft_checks_timeout
    # soft check를 미리 실행했다면 그 LLM 호출 수를 meta에 반영하기 위해 보관합니다.
    soft_check_calls = prefetched_soft_check_calls
    if prefetched_soft_checks is not None:
        soft_checks = [*prefetched_soft_checks]
    else:
        soft_checks = [*_fallback_soft_checks(snapshot)]
    if use_llm and prefetched_soft_checks is None:
        llm_soft_checks, soft_checks_timeout = await _llm_soft_checks(snapshot)
        soft_checks.extend(llm_soft_checks)
    if soft_check_calls is None:
        soft_check_calls = 1 if llm_configured else 0
    fallback_summary = _fallback_summary(failed_checks, suggestions)
    summary, narrator_calls = (
        await _llm_narrate(
            checks=checks,
            risks=risks,
            workloads=workloads,
            suggestions=suggestions,
            fallback_summary=fallback_summary,
        )
        if use_llm and failed_checks
        else (fallback_summary, 0)
    )
    narrator_fallback_template = narrator_calls > 0 and summary == fallback_summary
    response = RiskResponse(
        project_id=snapshot.project.project_id,
        checks=checks,
        soft_checks=soft_checks[:5],
        task_risk_levels=risks,
        member_workload=workloads,
        blockers_failed=blockers_failed,
        suggestions=suggestions,
        summary=summary,
    )
    object.__setattr__(
        response,
        "_agent_meta",
        {
            "soft_check_calls": soft_check_calls,
            "narrator_calls": narrator_calls,
            "soft_checks_timeout": soft_checks_timeout,
            "narrator_fallback_template": narrator_fallback_template,
        },
    )
    return response


async def prefetch_risk_soft_checks(
    snapshot: ProjectSnapshot,
    use_llm: bool = True,
) -> tuple[list[SoftCheck], bool, int]:
    soft_checks = [*_fallback_soft_checks(snapshot)]
    if not use_llm:
        return soft_checks, False, 0
    llm_soft_checks, soft_checks_timeout = await _llm_soft_checks(snapshot)
    soft_checks.extend(llm_soft_checks)
    return soft_checks, soft_checks_timeout, 1 if llm_client.configured else 0


class _SequentialRiskGraph:
    async def ainvoke(self, state: dict):
        return {
            "risk": await run_risk(
                state["snapshot"],
                state["priority"],
                state.get("schedule"),
                state["now"],
                state.get("use_llm", True),
                state.get("prefetched_soft_checks"),
                state.get("prefetched_soft_checks_timeout", False),
                state.get("prefetched_soft_check_calls"),
            )
        }


def _build_risk_subgraph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ModuleNotFoundError:
        return _SequentialRiskGraph()

    async def run_node(state: dict):
        return await _SequentialRiskGraph().ainvoke(state)

    graph = StateGraph(dict)
    graph.add_node("run_risk", run_node)
    graph.add_edge(START, "run_risk")
    graph.add_edge("run_risk", END)
    return graph.compile()


risk_subgraph = _build_risk_subgraph()
