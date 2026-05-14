import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


class RiskPmCopyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 7, 9, 0, tzinfo=timezone(timedelta(hours=9)))

    def _unschedulable_snapshot(self):
        from app.schemas import ProjectSnapshot

        fixture_path = Path(__file__).parent / "fixtures" / "e2e" / "scenario_2_unschedulable.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return ProjectSnapshot(**payload["snapshot"])

    def test_deadline_fallback_summary_uses_pm_copy_when_llm_narrator_is_rejected(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule

        class InvalidNarratorLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    return {"summary": "deadline_feasibility 때문에 999시간 지연됩니다."}
                return {"soft_checks": []}

        snapshot = self._unschedulable_snapshot()
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

        with patch("app.agents.risk.llm_client", InvalidNarratorLlm(), create=True):
            risk = asyncio.run(run_risk(snapshot, priority, schedule, self.now, use_llm=True))

        self.assertNotIn("deadline_feasibility", risk.summary)
        self.assertNotIn("Blocker 체크", risk.summary)
        self.assertIn("마감일까지 완료 가능성", risk.summary)
        self.assertIn("마감 전 자동 배치할 수 없는 Task", risk.summary)
        self.assertIn("마감 전 8h 작업", risk.summary)
        self.assertIn("마감일", risk.summary)
        self.assertEqual(getattr(risk, "_agent_meta")["narrator_calls"], 2)

    def test_deadline_unschedulable_suggestion_names_task_and_pm_actions(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule

        snapshot = self._unschedulable_snapshot()
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

        risk = asyncio.run(run_risk(snapshot, priority, schedule, self.now, use_llm=False))

        suggestion = next(item for item in risk.suggestions if "deadline_feasibility" in item.fixes_check_ids)
        self.assertNotIn("deadline_feasibility", suggestion.user_facing_text)
        self.assertIn("마감 전 8h 작업", suggestion.user_facing_text)
        self.assertIn("마감일", suggestion.user_facing_text)
        self.assertIn(suggestion.action.to[:10], suggestion.user_facing_text)
        self.assertNotIn("PM 조치:", suggestion.user_facing_text)

    def test_no_capacity_suggestion_extends_deadline_with_applicable_patch(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule
        from app.api.routes import _apply_risk_suggestions

        snapshot = self._unschedulable_snapshot()
        original_deadline = snapshot.tasks[0].deadline
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

        risk = asyncio.run(run_risk(snapshot, priority, schedule, self.now, use_llm=False))

        suggestion = next(item for item in risk.suggestions if "deadline_feasibility" in item.fixes_check_ids)
        self.assertEqual(suggestion.action.type, "reschedule")
        self.assertEqual(suggestion.action.target_task_id, "task_NOCAP001")
        self.assertEqual(suggestion.action.from_, original_deadline.isoformat())
        self.assertIsNotNone(suggestion.action.to)
        suggested_deadline = datetime.fromisoformat(suggestion.action.to)
        self.assertGreater(suggested_deadline, original_deadline)
        self.assertIn(suggestion.action.to[:10], suggestion.user_facing_text)

        simulated = _apply_risk_suggestions(snapshot, [suggestion])
        self.assertEqual(simulated.tasks[0].deadline, suggested_deadline)

    def test_predecessor_incomplete_suggestion_removes_blocking_dependency_patch(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule
        from app.api.routes import _apply_risk_suggestions
        from app.schemas import ImportanceLevel

        snapshot = self._unschedulable_snapshot()
        blocker = snapshot.tasks[0].model_copy(
            update={
                "task_id": "task_BLOCK001",
                "title": "선행 계약 확정",
                "importance": ImportanceLevel.low,
                "estimated_hours": None,
                "predecessor_ids": [],
            }
        )
        target = snapshot.tasks[0].model_copy(
            update={
                "task_id": "task_CHILD001",
                "title": "후행 개발 착수",
                "importance": ImportanceLevel.critical,
                "estimated_hours": 2,
                "deadline": self.now.replace(hour=18),
                "predecessor_ids": ["task_BLOCK001"],
            }
        )
        snapshot.tasks = [blocker, target]
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))
        self.assertTrue(
            any(
                item.task_id == "task_CHILD001" and "predecessor_incomplete" in item.reasons
                for item in schedule.unschedulable
            )
        )

        risk = asyncio.run(run_risk(snapshot, priority, schedule, self.now, use_llm=False))

        suggestion = next(item for item in risk.suggestions if "dependency_correctness" in item.fixes_check_ids)
        self.assertEqual(suggestion.action.type, "remove_predecessor")
        self.assertEqual(suggestion.action.target_task_id, "task_CHILD001")
        self.assertEqual(suggestion.action.to, "task_BLOCK001")
        self.assertIn("후행 개발 착수", suggestion.user_facing_text)
        self.assertIn("선행 계약 확정", suggestion.user_facing_text)

        simulated = _apply_risk_suggestions(snapshot, [suggestion])
        child = next(task for task in simulated.tasks if task.task_id == "task_CHILD001")
        self.assertEqual(child.predecessor_ids, [])


if __name__ == "__main__":
    unittest.main()
