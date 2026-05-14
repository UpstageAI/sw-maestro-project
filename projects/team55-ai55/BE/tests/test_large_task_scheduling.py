import asyncio
import unittest
from datetime import datetime, timedelta, timezone


class LargeTaskSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 11, 9, 0, tzinfo=timezone(timedelta(hours=9)))

    def _snapshot(self):
        starts_at = self.now.isoformat()
        return {
            "project": {
                "project_id": "proj_LARGET01",
                "name": "Large task scheduling",
                "goal": "Ship a 4 week MVP with realistic multi-day tasks.",
                "starts_at": "2026-05-11",
                "ends_at": "2026-06-07",
                "default_working_hours": {
                    "weekday": {"start": "09:00", "end": "18:00", "enabled": True},
                    "weekend": {"start": "10:00", "end": "16:00", "enabled": False},
                },
                "timezone": "Asia/Seoul",
            },
            "members": [
                {
                    "member_id": "mem_ALPHA1",
                    "name": "Backend",
                    "role": "Backend",
                    "weekly_capacity_hours": 40,
                    "available_hours": [
                        {"day_of_week": day, "start": "09:00", "end": "18:00"}
                        for day in range(5)
                    ],
                }
            ],
            "tasks": [
                {
                    "task_id": "task_DESIGN01",
                    "project_id": "proj_LARGET01",
                    "milestone_id": None,
                    "title": "API 계약 설계",
                    "description": "분석 API 계약을 확정한다.",
                    "assignee_id": "mem_ALPHA1",
                    "deadline": (self.now + timedelta(days=1)).isoformat(),
                    "importance": "critical",
                    "estimated_hours": 4,
                    "status": "todo",
                    "progress_percent": 0,
                    "delay_reason": None,
                    "predecessor_ids": [],
                    "created_at": starts_at,
                    "updated_at": starts_at,
                },
                {
                    "task_id": "task_IMPL0001",
                    "project_id": "proj_LARGET01",
                    "milestone_id": None,
                    "title": "일정 추천 및 승인 기능 구현",
                    "description": "하루 근무창보다 큰 구현 Task를 여러 근무 블록으로 진행한다.",
                    "assignee_id": "mem_ALPHA1",
                    "deadline": (self.now + timedelta(days=5)).isoformat(),
                    "importance": "critical",
                    "estimated_hours": 12,
                    "status": "todo",
                    "progress_percent": 0,
                    "delay_reason": None,
                    "predecessor_ids": ["task_DESIGN01"],
                    "created_at": starts_at,
                    "updated_at": starts_at,
                },
                {
                    "task_id": "task_RISK0001",
                    "project_id": "proj_LARGET01",
                    "milestone_id": None,
                    "title": "리스크 분석 기능 구현",
                    "description": "앞선 구현 Task가 배치되면 이어서 진행한다.",
                    "assignee_id": "mem_ALPHA1",
                    "deadline": (self.now + timedelta(days=7)).isoformat(),
                    "importance": "high",
                    "estimated_hours": 4,
                    "status": "todo",
                    "progress_percent": 0,
                    "delay_reason": None,
                    "predecessor_ids": ["task_IMPL0001"],
                    "created_at": starts_at,
                    "updated_at": starts_at,
                },
            ],
            "milestones": [],
            "calendar_events": [],
        }

    def test_large_task_is_split_into_multiple_work_blocks_before_deadline(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

        self.assertNotIn("task_IMPL0001", {item.task_id for item in schedule.unschedulable})
        proposal = next(item for item in schedule.slot_proposals if item.task_id == "task_IMPL0001")
        selected = proposal.candidate_slots[proposal.selected_index]
        self.assertGreaterEqual(len(selected.time_blocks), 3)
        self.assertLessEqual(selected.time_blocks[-1].ends_at, snapshot.tasks[1].deadline)

    def test_risk_summary_uses_pm_copy_not_raw_check_id_for_deadline_failure(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        payload = self._snapshot()
        payload["tasks"][1]["deadline"] = (self.now + timedelta(days=1)).isoformat()
        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

        risk = asyncio.run(run_risk(snapshot, priority, schedule, self.now, use_llm=False))

        self.assertNotIn("deadline_feasibility", risk.summary)
        self.assertIn("마감일까지 완료 가능성", risk.summary)
        self.assertTrue(
            any("일정 추천 및 승인 기능 구현" in suggestion.user_facing_text for suggestion in risk.suggestions)
        )
