import asyncio
from datetime import datetime, timedelta, timezone


def _snapshot(now: datetime) -> dict:
    starts_at = now.isoformat()
    return {
        "project": {
            "project_id": "proj_MULTIB01",
            "name": "Multi-block schedule regression",
            "goal": "Schedule long implementation tasks across working days.",
            "starts_at": "2026-05-06",
            "ends_at": "2026-06-30",
            "default_working_hours": {
                "weekday": {"start": "09:00", "end": "18:00", "enabled": True},
                "weekend": {"start": "10:00", "end": "16:00", "enabled": False},
            },
            "timezone": "Asia/Seoul",
        },
        "members": [
            {
                "member_id": "mem_MULTI1",
                "name": "Backend Owner",
                "role": "Backend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        ],
        "tasks": [
            {
                "task_id": "task_LONG0001",
                "project_id": "proj_MULTIB01",
                "milestone_id": None,
                "title": "Implement planning API",
                "description": "A 10h task cannot fit in one 09-18 window.",
                "assignee_id": "mem_MULTI1",
                "deadline": (now + timedelta(days=7)).isoformat(),
                "importance": "critical",
                "estimated_hours": 10,
                "status": "todo",
                "progress_percent": 0,
                "delay_reason": None,
                "predecessor_ids": [],
                "created_at": starts_at,
                "updated_at": starts_at,
            },
            {
                "task_id": "task_SHORT001",
                "project_id": "proj_MULTIB01",
                "milestone_id": None,
                "title": "Review implementation notes",
                "description": "A short task should fit into the free 17-18 block.",
                "assignee_id": "mem_MULTI1",
                "deadline": (now + timedelta(days=7)).isoformat(),
                "importance": "high",
                "estimated_hours": 1,
                "status": "todo",
                "progress_percent": 0,
                "delay_reason": None,
                "predecessor_ids": [],
                "created_at": starts_at,
                "updated_at": starts_at,
            },
            {
                "task_id": "task_LONG0002",
                "project_id": "proj_MULTIB01",
                "milestone_id": None,
                "title": "Implement dashboard workflow",
                "description": "A 12h child task should schedule after the predecessor.",
                "assignee_id": "mem_MULTI1",
                "deadline": (now + timedelta(days=10)).isoformat(),
                "importance": "critical",
                "estimated_hours": 12,
                "status": "todo",
                "progress_percent": 0,
                "delay_reason": None,
                "predecessor_ids": ["task_LONG0001"],
                "created_at": starts_at,
                "updated_at": starts_at,
            },
        ],
        "milestones": [],
        "calendar_events": [],
    }


def test_schedule_splits_long_tasks_across_working_day_blocks():
    from app.agents.schedule import run_schedule
    from app.schemas import PriorityFactors, PriorityResponse, PriorityScore, ProjectSnapshot

    now = datetime(2026, 5, 6, 9, 0, tzinfo=timezone(timedelta(hours=9)))
    snapshot = ProjectSnapshot(**_snapshot(now))
    factors = PriorityFactors(
        deadline_pressure=1,
        importance=1,
        predecessor_pressure=0,
        progress_gap=1,
        overload_penalty=0,
    )
    priority = PriorityResponse(
        project_id=snapshot.project.project_id,
        tasks_priority=[
            PriorityScore(
                task_id="task_LONG0001",
                score=100,
                rank=1,
                factors=factors,
                evidence_facts=["Regression order fixture"],
                rationale="Long predecessor first.",
            ),
            PriorityScore(
                task_id="task_SHORT001",
                score=95,
                rank=2,
                factors=factors,
                evidence_facts=["Regression order fixture"],
                rationale="Short task should use free capacity.",
            ),
            PriorityScore(
                task_id="task_LONG0002",
                score=90,
                rank=3,
                factors=factors,
                evidence_facts=["Regression order fixture"],
                rationale="Long child after predecessor.",
            ),
        ],
        task_decompositions=[],
        task_assignments=[],
        warnings=[],
    )

    schedule = asyncio.run(run_schedule(snapshot, priority, now, horizon_days=14, use_llm=False))

    unschedulable_by_task = {item.task_id: item for item in schedule.unschedulable}
    assert "task_LONG0001" not in unschedulable_by_task
    assert "task_LONG0002" not in unschedulable_by_task
    assert {proposal.task_id for proposal in schedule.slot_proposals} == {
        "task_LONG0001",
        "task_SHORT001",
        "task_LONG0002",
    }

    slots = {
        proposal.task_id: proposal.candidate_slots[proposal.selected_index]
        for proposal in schedule.slot_proposals
    }
    assert slots["task_LONG0001"].ends_at > slots["task_LONG0001"].starts_at.replace(hour=18)
    assert len(slots["task_LONG0001"].time_blocks) > 1
    short_proposal = next(
        proposal for proposal in schedule.slot_proposals if proposal.task_id == "task_SHORT001"
    )
    assert any(
        candidate.starts_at == now.replace(hour=17)
        and candidate.ends_at == now.replace(hour=18)
        for candidate in short_proposal.candidate_slots
    )
    assert slots["task_LONG0001"].ends_at <= slots["task_LONG0002"].starts_at
