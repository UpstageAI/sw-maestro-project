# Milestone Suggest v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the loose one-shot milestone suggestion prompt with deterministic date slots plus LLM-generated Korean deliverable names and rationales.

**Architecture:** Add a focused milestone suggestion service that owns slot count, slot dates, mode detection, compact LLM payloads, LLM result validation, and goal-aware fallback. Keep the FastAPI response contract unchanged and have the route call the service. Existing FE mapping does not change.

**Tech Stack:** FastAPI, Pydantic v2 models, Python `unittest`, existing in-memory cache and Upstage-compatible `llm_client`.

---

## File Structure

- Create `BE/app/services/milestone_suggester.py`: pure helper functions and an async `suggest_project_milestones()` entrypoint.
- Modify `BE/app/api/routes.py`: compute a broader cache key, call the helper, and keep metrics/cache behavior.
- Modify `BE/tests/test_backend_contracts.py`: add route-level contract tests for v2 behavior.
- Keep `FE/src/app/apiClient.ts` unchanged because the API response shape remains `name`, `due_date`, `ai_rationale`.

### Task 1: Red Tests For Milestone Suggest v2

**Files:**
- Modify: `BE/tests/test_backend_contracts.py`

- [ ] **Step 1: Add a setup-mode fallback test**

Add this test after `test_milestone_suggest_records_schema_failure_for_invalid_llm_payload`:

```python
    def test_milestone_suggest_setup_fallback_uses_duration_slots_and_goal(self):
        from app.services.cache import milestone_cache

        snapshot = copy.deepcopy(self._snapshot())
        snapshot["project"]["goal"] = "고객 상담 자동화 MVP"
        snapshot["project"]["starts_at"] = "2026-05-01"
        snapshot["project"]["ends_at"] = "2026-05-30"
        snapshot["tasks"] = []
        milestone_cache._items.clear()

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/milestones:suggest",
            json={"snapshot": snapshot, "max_milestones": 8},
        )

        self.assertEqual(response.status_code, 200)
        milestones = response.json()["proposed_milestones"]
        self.assertEqual(len(milestones), 4)
        self.assertEqual(milestones[-1]["due_date"], "2026-05-30")
        self.assertTrue(all("고객 상담 자동화 MVP" in item["name"] for item in milestones[:3]))
        self.assertTrue(all("due_date" in item for item in milestones))
```

- [ ] **Step 2: Add an LLM slot validation test**

Add this test after the setup fallback test:

```python
    def test_milestone_suggest_uses_backend_slots_and_ignores_llm_dates(self):
        from app.services.cache import milestone_cache

        class SlotLlm:
            configured = True

            def __init__(self):
                self.payload = None

            async def chat_json(self, **kwargs):
                self.payload = json.loads(kwargs["user"])
                return {
                    "milestones": [
                        {
                            "slot_index": 1,
                            "name": "요구사항 산출물 확정",
                            "due_date": "2099-01-01",
                            "ai_rationale": "초기 범위를 확정합니다.",
                        },
                        {
                            "slot_index": 2,
                            "name": "핵심 기능 산출물 완성",
                            "due_date": "2099-01-02",
                            "ai_rationale": "핵심 구현을 완료합니다.",
                        },
                    ]
                }

        fake_llm = SlotLlm()
        snapshot = copy.deepcopy(self._snapshot())
        snapshot["project"]["starts_at"] = "2026-05-01"
        snapshot["project"]["ends_at"] = "2026-05-14"
        snapshot["tasks"] = []
        milestone_cache._items.clear()

        with patch("app.api.routes.llm_client", fake_llm, create=True):
            response = self.client.post(
                "/v1/projects/proj_ABCDEF12/milestones:suggest",
                json={"snapshot": snapshot, "max_milestones": 8},
            )

        self.assertEqual(response.status_code, 200)
        milestones = response.json()["proposed_milestones"]
        self.assertEqual(len(milestones), 3)
        self.assertEqual(milestones[0]["name"], "요구사항 산출물 확정")
        self.assertNotEqual(milestones[0]["due_date"], "2099-01-01")
        self.assertEqual(milestones[-1]["due_date"], "2026-05-14")
        self.assertEqual(fake_llm.payload["mode"], "setup_mode")
        self.assertEqual(len(fake_llm.payload["slots"]), 3)
```

- [ ] **Step 3: Add an execution-mode payload and cache-key test**

Add this test after the slot validation test:

```python
    def test_milestone_suggest_execution_mode_sends_task_summary_and_cache_tracks_tasks(self):
        from app.services.cache import milestone_cache

        class CountingLlm:
            configured = True

            def __init__(self):
                self.calls = 0
                self.payloads = []

            async def chat_json(self, **kwargs):
                self.calls += 1
                payload = json.loads(kwargs["user"])
                self.payloads.append(payload)
                return {
                    "milestones": [
                        {
                            "slot_index": slot["slot_index"],
                            "name": f"{slot['position']} 산출물 확정",
                            "ai_rationale": "제공된 task 맥락을 기준으로 산출물을 정리합니다.",
                        }
                        for slot in payload["slots"]
                    ]
                }

        fake_llm = CountingLlm()
        snapshot = copy.deepcopy(self._snapshot())
        second_task = copy.deepcopy(snapshot["tasks"][0])
        second_task["task_id"] = "task_BRAVO001"
        second_task["title"] = "React 대시보드 구현"
        second_task["description"] = "사용자 대시보드 화면을 구현한다."
        third_task = copy.deepcopy(snapshot["tasks"][0])
        third_task["task_id"] = "task_CHARLIE1"
        third_task["title"] = "배포 검증"
        third_task["description"] = "스테이징 배포 후 핵심 플로우를 검증한다."
        snapshot["tasks"] = [snapshot["tasks"][0], second_task, third_task]
        milestone_cache._items.clear()

        with patch("app.api.routes.llm_client", fake_llm, create=True):
            first = self.client.post("/v1/projects/proj_ABCDEF12/milestones:suggest", json={"snapshot": snapshot, "max_milestones": 8})
            second = self.client.post("/v1/projects/proj_ABCDEF12/milestones:suggest", json={"snapshot": snapshot, "max_milestones": 8})
            changed = copy.deepcopy(snapshot)
            changed["tasks"][1]["title"] = "React 대시보드 구현 변경"
            third = self.client.post("/v1/projects/proj_ABCDEF12/milestones:suggest", json={"snapshot": changed, "max_milestones": 8})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 200)
        self.assertEqual(fake_llm.calls, 2)
        self.assertEqual(fake_llm.payloads[0]["mode"], "execution_mode")
        self.assertEqual(fake_llm.payloads[0]["task_summary"]["total"], 3)
        self.assertIn("React 대시보드 구현", fake_llm.payloads[0]["task_summary"]["titles"])
```

- [ ] **Step 4: Run tests to verify RED**

Run:

```bash
cd BE && pytest tests/test_backend_contracts.py -k 'milestone_suggest' -q
```

Expected: the new tests fail because milestone v2 slot generation and slot-indexed LLM parsing do not exist yet.

### Task 2: Implement Milestone Suggester Service

**Files:**
- Create: `BE/app/services/milestone_suggester.py`

- [ ] **Step 1: Add the service module**

Create these functions and dataclasses:

```python
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.schemas import ProjectSnapshot, ProposedMilestone


@dataclass(frozen=True)
class MilestoneSlot:
    slot_index: int
    due_date: date
    position: str


def useful_task_count(snapshot: ProjectSnapshot) -> int:
    return sum(1 for task in snapshot.tasks if task.title.strip())


def milestone_mode(snapshot: ProjectSnapshot) -> str:
    return "execution_mode" if useful_task_count(snapshot) >= 3 else "setup_mode"


def target_milestone_count(snapshot: ProjectSnapshot, max_milestones: int) -> int:
    days = max((snapshot.project.ends_at - snapshot.project.starts_at).days + 1, 1)
    use_high = milestone_mode(snapshot) == "execution_mode"
    if days <= 7:
        target = 3 if use_high else 2
    elif days <= 21:
        target = 4 if use_high else 3
    elif days <= 45:
        target = 5 if use_high else 4
    elif days <= 90:
        target = 6 if use_high else 5
    else:
        target = 8 if use_high else 6
    return max(1, min(target, max_milestones, 8))
```

- [ ] **Step 2: Add slot generation and compact payload helpers**

Use deterministic slots and compact task/team summaries:

```python
def build_milestone_slots(snapshot: ProjectSnapshot, max_milestones: int) -> list[MilestoneSlot]:
    count = target_milestone_count(snapshot, max_milestones)
    start = snapshot.project.starts_at
    end = snapshot.project.ends_at
    total_days = max((end - start).days, 0)
    if count == 1 or total_days == 0:
        return [MilestoneSlot(slot_index=1, due_date=end, position="final")]

    offsets: list[int] = []
    for index in range(count):
        if index == count - 1:
            offset = total_days
        elif index == 0:
            offset = max(1, round(total_days / count))
        else:
            offset = round(total_days * (index + 1) / count)
        offsets.append(max(0, min(offset, total_days)))

    seen: set[date] = set()
    slots: list[MilestoneSlot] = []
    for index, offset in enumerate(offsets):
        due_date = start + timedelta(days=offset)
        while due_date in seen and due_date < end:
            due_date += timedelta(days=1)
        seen.add(due_date)
        position = "final" if index == count - 1 else "early" if index == 0 else "middle"
        slots.append(MilestoneSlot(slot_index=index + 1, due_date=due_date, position=position))
    return slots


def build_milestone_llm_payload(snapshot: ProjectSnapshot, slots: list[MilestoneSlot]) -> dict[str, Any]:
    return {
        "project": {
            "goal": snapshot.project.goal,
            "starts_at": snapshot.project.starts_at.isoformat(),
            "ends_at": snapshot.project.ends_at.isoformat(),
            "timezone": snapshot.project.timezone,
        },
        "mode": milestone_mode(snapshot),
        "slots": [
            {"slot_index": slot.slot_index, "due_date": slot.due_date.isoformat(), "position": slot.position}
            for slot in slots
        ],
        "team_summary": {
            "member_count": len(snapshot.members),
            "roles": [member.role for member in snapshot.members if member.role][:8],
        },
        "task_summary": {
            "total": len(snapshot.tasks),
            "titles": [task.title for task in snapshot.tasks if task.title.strip()][:12],
        },
    }
```

- [ ] **Step 3: Add validation, fallback, and cache signature helpers**

Implement LLM repair and deterministic fallback:

```python
def compact_goal_keyword(goal: str) -> str:
    normalized = re.sub(r"\s+", " ", goal).strip()
    return normalized[:28].strip()


def fallback_for_slot(snapshot: ProjectSnapshot, slot: MilestoneSlot) -> ProposedMilestone:
    keyword = compact_goal_keyword(snapshot.project.goal)
    templates = {
        "early": ("요구사항 산출물 확정", "프로젝트 목표를 실행 가능한 범위와 기준으로 먼저 고정합니다."),
        "middle": ("핵심 산출물 완성", "핵심 작업 범위를 마감 전에 검증 가능한 산출물로 묶습니다."),
        "final": ("검증 및 출시 준비", "최종 검증과 전달 준비를 마쳐 프로젝트 종료 기준을 맞춥니다."),
    }
    suffix, rationale = templates.get(slot.position, templates["middle"])
    name = f"{keyword} {suffix}".strip() if keyword else suffix
    return ProposedMilestone(name=name[:80], due_date=slot.due_date, ai_rationale=rationale)


def build_task_signature(snapshot: ProjectSnapshot) -> str:
    task_bits = [
        {
            "task_id": task.task_id,
            "title": task.title,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "assignee_id": task.assignee_id,
            "estimated_hours": task.estimated_hours,
            "predecessor_ids": task.predecessor_ids,
        }
        for task in snapshot.tasks
    ]
    return hashlib.sha256(repr(task_bits).encode()).hexdigest()
```

- [ ] **Step 4: Add the async entrypoint**

The entrypoint calls the LLM, validates slot-indexed results, fills gaps, and returns `(milestones, schema_success)`:

```python
async def suggest_project_milestones(snapshot: ProjectSnapshot, max_milestones: int, llm_client) -> tuple[list[ProposedMilestone], bool | None]:
    slots = build_milestone_slots(snapshot, max_milestones)
    payload = build_milestone_llm_payload(snapshot, slots)
    llm_payload = await llm_client.chat_json(
        system=(
            "You create Korean project milestone labels for fixed backend-provided slots. Output JSON only: "
            "{\"milestones\":[{\"slot_index\":1,\"name\":\"...\",\"ai_rationale\":\"...\"}]}. "
            "Return exactly one milestone per supplied slot. Do not invent members, tasks, dates, external facts, or personal judgments. "
            "Do not change due dates. Names must be deliverable-centered, not phase-centered. Avoid vague names like 기획 단계 or 개발 단계."
        ),
        user=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        purpose="milestone_suggest",
        temperature=0,
    )
```

The final implementation must import `json`, validate `slot_index`, ignore any LLM `due_date`, and fallback for missing or invalid slots.

- [ ] **Step 5: Run milestone tests**

Run:

```bash
cd BE && pytest tests/test_backend_contracts.py -k 'milestone_suggest' -q
```

Expected: failures now point to route wiring/cache key still using the old logic.

### Task 3: Wire Route And Cache Key

**Files:**
- Modify: `BE/app/api/routes.py`

- [ ] **Step 1: Import helper functions**

Import:

```python
from app.services.milestone_suggester import build_task_signature, suggest_project_milestones
```

- [ ] **Step 2: Replace the old inline LLM milestone block**

Use:

```python
goal_hash = hashlib.sha256(req.snapshot.project.goal.encode()).hexdigest()
task_signature = build_task_signature(req.snapshot)
cache_key = (
    "milestones",
    project_id,
    goal_hash,
    req.snapshot.project.starts_at.isoformat(),
    req.snapshot.project.ends_at.isoformat(),
    req.max_milestones,
    task_signature,
)
```

Then call:

```python
if llm_client.configured:
    record_llm_call("milestone_suggest")
proposed, schema_success = await suggest_project_milestones(req.snapshot, req.max_milestones, llm_client)
if schema_success is not None:
    record_llm_schema_result("milestone_suggest", schema_success)
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
cd BE && pytest tests/test_backend_contracts.py -k 'milestone_suggest' -q
```

Expected: all milestone suggestion tests pass.

### Task 4: Final Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
cd BE && pytest tests/test_backend_contracts.py -k 'milestone_suggest or openapi_exposes_documented_api_contract_paths' -q
```

Expected: pass.

- [ ] **Step 2: Check worktree scope**

Run:

```bash
git status --short
git diff --stat
```

Expected: milestone v2 changes are limited to the new service, route, tests, and plan docs. Pre-existing dirty task-assignment files may still be present and must not be reverted.
