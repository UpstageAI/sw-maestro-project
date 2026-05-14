# Schedule Engine Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the Schedule Agent so it produces a real calendar-like schedule inside the existing API contract.

**Architecture:** Keep `ScheduleResponse`, `SlotProposal`, and FE/Risk contracts unchanged. Rewrite `BE/app/agents/schedule.py` internally around `priority-aware ordering -> greedy pack -> limited repair -> final validation -> LLM rerank -> final validation/fallback`.

**Tech Stack:** Python 3, FastAPI backend models in `BE/app/schemas.py`, existing backend tests in `BE/tests/test_backend_contracts.py`, existing metrics/LLM client wrappers.

---

## Scope

Do not modify `BE/app/agents/risk.py`. Do not change FE files or API response schemas for this pass. Keep the current MVP rule that one task maps to one selected slot; long task block splitting remains a utility only.

## File Structure

- Modify: `BE/app/agents/schedule.py`
  - Owns priority-aware ordering, candidate generation, fit scoring, selected schedule validation, limited repair, and LLM rerank verification.
- Modify: `BE/tests/test_backend_contracts.py`
  - Adds regression tests for dependency ordering, real calendar packing, density repair, and strict rerank fallback.
- Modify: `docs/specs/03-agent-schedule-spec.md`
  - Records the intended Schedule Engine behavior and boundaries.

## Task 1: Lock Priority-Aware Topological Ordering

**Files:**
- Modify: `BE/tests/test_backend_contracts.py`
- Modify: `BE/app/agents/schedule.py`

- [ ] **Step 1: Add failing dependency-order regression test**

Add a backend test that creates two tasks where the child has higher priority than the predecessor, then asserts the predecessor is scheduled first and the child starts after the predecessor ends.

```python
def test_schedule_priority_order_does_not_break_dependencies(self):
    from app.agents.priority import run_priority
    from app.agents.schedule import run_schedule
    from app.schemas import ProjectSnapshot

    payload = self._snapshot()
    predecessor = payload["tasks"][0]
    child = {**predecessor}
    predecessor["task_id"] = "task_SETUP001"
    predecessor["title"] = "Setup API contract"
    predecessor["importance"] = "medium"
    predecessor["estimated_hours"] = 2
    predecessor["predecessor_ids"] = []
    child["task_id"] = "task_CHILD001"
    child["title"] = "Launch critical integration"
    child["importance"] = "critical"
    child["estimated_hours"] = 2
    child["predecessor_ids"] = ["task_SETUP001"]
    payload["tasks"] = [child, predecessor]

    snapshot = ProjectSnapshot(**payload)
    priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
    schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

    slot_by_task = {
        proposal.task_id: proposal.candidate_slots[proposal.selected_index]
        for proposal in schedule.slot_proposals
    }
    self.assertLessEqual(slot_by_task["task_SETUP001"].ends_at, slot_by_task["task_CHILD001"].starts_at)
```

- [ ] **Step 2: Run the test and verify it fails on current ordering**

Run:

```bash
PYTHONPATH=BE python3 -m pytest BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_priority_order_does_not_break_dependencies -q
```

Expected: FAIL before implementation because the current post-topo priority sort can place the child before its predecessor.

- [ ] **Step 3: Implement `priority_aware_topo_sort`**

Add a helper in `BE/app/agents/schedule.py` near the ordering helpers.

```python
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
```

Replace the current `topo_sort(...); ordered.sort(...)` pair with:

```python
ordered = priority_aware_topo_sort(
    [t for t in snapshot.tasks if t.status not in (TaskStatus.done, TaskStatus.cancelled)],
    priority_by_task,
)
```

- [ ] **Step 4: Run the focused test**

Run:

```bash
PYTHONPATH=BE python3 -m pytest BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_priority_order_does_not_break_dependencies -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add BE/app/agents/schedule.py BE/tests/test_backend_contracts.py
git commit -m "fix: preserve dependencies in schedule ordering"
```

## Task 2: Schedule Active Predecessors Instead of Dropping Children

**Files:**
- Modify: `BE/tests/test_backend_contracts.py`
- Modify: `BE/app/agents/schedule.py`

- [ ] **Step 1: Add failing test for unfinished predecessor planned in same run**

```python
def test_schedule_places_child_after_unfinished_predecessor_in_same_run(self):
    from app.agents.priority import run_priority
    from app.agents.schedule import run_schedule
    from app.schemas import ProjectSnapshot

    payload = self._snapshot()
    first = payload["tasks"][0]
    second = {**first}
    first["task_id"] = "task_FIRST001"
    first["title"] = "Write API draft"
    first["status"] = "todo"
    first["estimated_hours"] = 2
    first["predecessor_ids"] = []
    second["task_id"] = "task_SECOND01"
    second["title"] = "Review API draft"
    second["status"] = "todo"
    second["estimated_hours"] = 2
    second["predecessor_ids"] = ["task_FIRST001"]
    payload["tasks"] = [second, first]

    snapshot = ProjectSnapshot(**payload)
    priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
    schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

    self.assertEqual(schedule.unschedulable, [])
    slot_by_task = {
        proposal.task_id: proposal.candidate_slots[proposal.selected_index]
        for proposal in schedule.slot_proposals
    }
    self.assertLessEqual(slot_by_task["task_FIRST001"].ends_at, slot_by_task["task_SECOND01"].starts_at)
```

- [ ] **Step 2: Run the test and verify it fails if child is marked `predecessor_incomplete`**

Run:

```bash
PYTHONPATH=BE python3 -m pytest BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_places_child_after_unfinished_predecessor_in_same_run -q
```

Expected: FAIL before implementation when incomplete predecessors are treated as an immediate unschedulable reason.

- [ ] **Step 3: Replace immediate incomplete-predecessor rejection**

In `run_schedule`, remove the unconditional `incomplete_preds` rejection. Instead, after computing ordered tasks, only mark `predecessor_incomplete` when an active predecessor exists but did not receive an `end_by_task` entry and is not already done/cancelled.

```python
missing_scheduled_predecessors = [
    pred_id
    for pred_id in task.predecessor_ids
    if pred_id in task_by_id
    and task_by_id[pred_id].status not in (TaskStatus.done, TaskStatus.cancelled)
    and pred_id not in end_by_task
]
if missing_scheduled_predecessors:
    reasons.append("predecessor_incomplete")
```

Keep the existing earliest-start calculation:

```python
earliest = now
for pred_id in task.predecessor_ids:
    if pred_id in end_by_task:
        earliest = max(earliest, end_by_task[pred_id])
```

- [ ] **Step 4: Run both dependency tests**

Run:

```bash
PYTHONPATH=BE python3 -m pytest \
  BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_priority_order_does_not_break_dependencies \
  BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_places_child_after_unfinished_predecessor_in_same_run -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add BE/app/agents/schedule.py BE/tests/test_backend_contracts.py
git commit -m "fix: schedule active predecessor chains"
```

## Task 3: Add Selected Schedule Validation and Density Guard

**Files:**
- Modify: `BE/tests/test_backend_contracts.py`
- Modify: `BE/app/agents/schedule.py`

- [ ] **Step 1: Add test that selected slots do not crowd into one hour bucket**

```python
def test_schedule_spreads_tasks_across_one_hour_buckets(self):
    from app.agents.priority import run_priority
    from app.agents.schedule import run_schedule
    from app.schemas import ProjectSnapshot

    payload = self._snapshot()
    base_task = payload["tasks"][0]
    payload["members"] = [
        {**payload["members"][0], "member_id": f"mem_SPREAD{i:02d}", "name": f"Member {i}"}
        for i in range(4)
    ]
    payload["tasks"] = []
    for i in range(4):
        task = {**base_task}
        task["task_id"] = f"task_SPREAD{i:02d}"
        task["title"] = f"Spread task {i}"
        task["assignee_id"] = f"mem_SPREAD{i:02d}"
        task["estimated_hours"] = 1
        task["predecessor_ids"] = []
        task["deadline"] = (self.now + timedelta(days=3)).isoformat()
        payload["tasks"].append(task)

    snapshot = ProjectSnapshot(**payload)
    priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
    schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

    buckets: dict[str, int] = {}
    for proposal in schedule.slot_proposals:
        slot = proposal.candidate_slots[proposal.selected_index]
        bucket = slot.starts_at.replace(minute=0, second=0, microsecond=0).isoformat()
        buckets[bucket] = buckets.get(bucket, 0) + 1
    self.assertLessEqual(max(buckets.values()), 2)
```

- [ ] **Step 2: Add validation helper**

Add a helper that returns violation strings for selected proposals.

```python
def validate_selected_schedule(
    *,
    snapshot: ProjectSnapshot,
    proposals: list[SlotProposal],
    allow_density_warning: bool = False,
) -> list[str]:
    violations: list[str] = []
    task_by_id = {task.task_id: task for task in snapshot.tasks}
    selected_by_task = {
        proposal.task_id: proposal.candidate_slots[proposal.selected_index]
        for proposal in proposals
        if 0 <= proposal.selected_index < len(proposal.candidate_slots)
    }

    for proposal in proposals:
        if proposal.selected_index < 0 or proposal.selected_index >= len(proposal.candidate_slots):
            violations.append(f"selected_index_oob:{proposal.task_id}")

    proposal_items = list(selected_by_task.items())
    for index, (task_id, slot) in enumerate(proposal_items):
        task = task_by_id.get(task_id)
        if task is None:
            continue
        if task.deadline and slot.ends_at > task.deadline:
            violations.append(f"deadline_exceeded:{task_id}")
        if not _is_within_working_window(snapshot, task, slot.starts_at, slot.ends_at):
            violations.append(f"working_window_violation:{task_id}")
        for pred_id in task.predecessor_ids:
            pred_slot = selected_by_task.get(pred_id)
            if pred_slot and pred_slot.ends_at > slot.starts_at:
                violations.append(f"dependency_inversion:{task_id}")
        for other_task_id, other_slot in proposal_items[index + 1:]:
            other_task = task_by_id.get(other_task_id)
            if other_task and task.assignee_id == other_task.assignee_id and _overlap(
                slot.starts_at, slot.ends_at, other_slot.starts_at, other_slot.ends_at
            ):
                violations.append(f"hard_overlap:{task_id}:{other_task_id}")

    bucket_counts: dict[str, int] = {}
    for slot in selected_by_task.values():
        bucket = slot.starts_at.replace(minute=0, second=0, microsecond=0).isoformat()
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    crowded = [bucket for bucket, count in bucket_counts.items() if count > 2]
    if crowded and not allow_density_warning:
        violations.extend(f"density_violation:{bucket}" for bucket in crowded)
    return violations
```

- [ ] **Step 3: Add density penalty to fit scoring**

Pass current virtual events to `compute_fit_score` and subtract a strong but bounded penalty for crowded project buckets.

```python
def _project_density_penalty(starts_at: datetime, events: list[InternalCalendarEvent]) -> int:
    bucket_start = starts_at.replace(minute=0, second=0, microsecond=0)
    bucket_end = bucket_start + timedelta(hours=1)
    count = sum(1 for event in events if _overlap(bucket_start, bucket_end, event.starts_at, event.ends_at))
    return min(30, max(0, count - 1) * 15)
```

Apply it after the existing raw fit score:

```python
score = max(0, score - _project_density_penalty(starts_at, events))
```

- [ ] **Step 4: Run density test**

Run:

```bash
PYTHONPATH=BE python3 -m pytest BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_spreads_tasks_across_one_hour_buckets -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add BE/app/agents/schedule.py BE/tests/test_backend_contracts.py
git commit -m "fix: spread schedule slots across crowded hours"
```

## Task 4: Implement Limited Repair

**Files:**
- Modify: `BE/tests/test_backend_contracts.py`
- Modify: `BE/app/agents/schedule.py`

- [ ] **Step 1: Add failing repair test**

Create a test where greedy selection causes a density violation, but choosing a second candidate for one same-assignee/dependency-related task fixes the response.

```python
def test_schedule_repairs_density_with_alternate_candidate(self):
    from app.agents.priority import run_priority
    from app.agents.schedule import run_schedule, validate_selected_schedule
    from app.schemas import ProjectSnapshot

    payload = self._snapshot()
    for event_index in range(2):
        payload["calendar_events"].append(
            {
                "event_id": f"evt_DENSITY{event_index}",
                "project_id": payload["project"]["project_id"],
                "task_id": None,
                "assignee_id": f"mem_OTHER{event_index}",
                "starts_at": self.now.replace(hour=9, minute=0).isoformat(),
                "ends_at": self.now.replace(hour=10, minute=0).isoformat(),
                "approved": True,
                "approved_at": None,
                "source": "ai_suggested",
            }
        )
    payload["tasks"][0]["estimated_hours"] = 1
    snapshot = ProjectSnapshot(**payload)
    priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
    schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

    self.assertEqual(validate_selected_schedule(snapshot=snapshot, proposals=schedule.slot_proposals), [])
```

- [ ] **Step 2: Implement repair helper**

Implement a small deterministic repair that tries alternate candidates for proposals involved in validation failures.

```python
def repair_schedule(
    *,
    snapshot: ProjectSnapshot,
    proposals: list[SlotProposal],
    max_rounds: int = 2,
) -> tuple[list[SlotProposal], list[str]]:
    repaired = list(proposals)
    warnings: list[str] = []
    for _round in range(max_rounds):
        violations = validate_selected_schedule(snapshot=snapshot, proposals=repaired)
        if not violations:
            return repaired, warnings
        changed = False
        for proposal_index, proposal in enumerate(repaired):
            for candidate_index in range(proposal.selected_index + 1, len(proposal.candidate_slots)):
                trial = list(repaired)
                trial[proposal_index] = proposal.model_copy(update={"selected_index": candidate_index})
                if not validate_selected_schedule(snapshot=snapshot, proposals=trial):
                    repaired = trial
                    changed = True
                    break
            if changed:
                break
        if not changed:
            warnings.extend(violations)
            return repaired, warnings
    warnings.extend(validate_selected_schedule(snapshot=snapshot, proposals=repaired, allow_density_warning=True))
    return repaired, warnings
```

- [ ] **Step 3: Call repair after deterministic packing**

After building deterministic `proposals`, call:

```python
proposals, repair_warnings = repair_schedule(snapshot=snapshot, proposals=proposals)
```

Convert unrepaired density warnings into schedule warnings without changing API schema:

```python
rerank_warnings = [*repair_warnings, *rerank_warnings]
```

- [ ] **Step 4: Run repair and existing schedule tests**

Run:

```bash
PYTHONPATH=BE python3 -m pytest \
  BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_repairs_density_with_alternate_candidate \
  BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_accepts_valid_llm_rerank_without_changing_candidate_slots \
  BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_reports_no_capacity_before_deadline_for_occupied_one_day_task -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add BE/app/agents/schedule.py BE/tests/test_backend_contracts.py
git commit -m "fix: repair invalid schedule selections"
```

## Task 5: Harden LLM Rerank Verification

**Files:**
- Modify: `BE/tests/test_backend_contracts.py`
- Modify: `BE/app/agents/schedule.py`

- [ ] **Step 1: Add tests for strict rerank contract**

Add tests that reject incomplete `ranked_indices`, duplicate indices, `selected_index != ranked_indices[0]`, and density violations after rerank.

```python
def test_schedule_rejects_incomplete_llm_ranked_indices(self):
    from app.agents.priority import run_priority
    from app.agents.schedule import run_schedule
    from app.schemas import ProjectSnapshot

    class FakeLlm:
        configured = True
        async def chat_json(self, **_):
            return {"rerankings": [{"task_index": 0, "task_id": "task_ALPHA001", "ranked_indices": [1], "selected_index": 1, "rationale": "후보 일부만 반환합니다."}]}

    snapshot = ProjectSnapshot(**self._snapshot())
    priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
    with patch("app.agents.schedule.llm_client", FakeLlm(), create=True):
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

    self.assertEqual(schedule.slot_proposals[0].selected_index, 0)
    self.assertEqual(schedule.slot_proposals[0].rerank_source, "deterministic")
    self.assertIn("rerank_violation:task_ALPHA001", schedule.warnings)
```

- [ ] **Step 2: Strengthen `verify_rerank`**

Update `verify_rerank` so every proposal requires exactly one reranking and every `ranked_indices` is an exact permutation.

```python
expected_indices = list(range(len(proposal.candidate_slots)))
if (
    not isinstance(ranked_indices, list)
    or sorted(ranked_indices) != expected_indices
    or selected_index != ranked_indices[0]
):
    violations.append(f"rerank_violation:{proposal.task_id}")
```

- [ ] **Step 3: Validate applied rerank globally before accepting**

Inside `_apply_llm_rerank`, after `verify_rerank` passes and before returning updated proposals, run:

```python
updated = _apply_verified_rerank(proposals, payload)
global_violations = validate_selected_schedule(snapshot=snapshot, proposals=updated)
if global_violations:
    record_llm_schema_result("schedule_rerank", False)
    record_llm_safety_result("schedule_rerank", False, global_violations[0])
    last_warnings = [f"rerank_violation:{proposal.task_id}" for proposal in proposals]
    continue
```

- [ ] **Step 4: Run rerank safety tests**

Run:

```bash
PYTHONPATH=BE python3 -m pytest \
  BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_rejects_incomplete_llm_ranked_indices \
  BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_rejects_invalid_llm_rerank_and_keeps_deterministic_selection \
  BE/tests/test_backend_contracts.py::BackendContractsTest::test_schedule_falls_back_when_llm_rerank_times_out -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add BE/app/agents/schedule.py BE/tests/test_backend_contracts.py
git commit -m "fix: enforce schedule rerank invariants"
```

## Task 6: Final Regression Gate

**Files:**
- Modify: `docs/specs/03-agent-schedule-spec.md` only if implementation discovers a documented invariant conflict.

- [ ] **Step 1: Run backend schedule-focused tests**

Run:

```bash
PYTHONPATH=BE python3 -m pytest BE/tests/test_backend_contracts.py -q
```

Expected: all backend contract tests pass.

- [ ] **Step 2: Run repo completion gate if live credentials are available**

Run:

```bash
npm run check:completion
```

Expected: local QA, live Upstage readiness, E2E, and completion checks pass. If live credentials are unavailable, record the exact failing readiness line and run `npm run qa:local` instead.

- [ ] **Step 3: Inspect diff scope**

Run:

```bash
git diff -- BE/app/agents/schedule.py BE/tests/test_backend_contracts.py docs/specs/03-agent-schedule-spec.md
```

Expected: no edits to `BE/app/agents/risk.py`, FE files, or API schemas.

- [ ] **Step 4: Commit final doc adjustments if any**

```bash
git add BE/app/agents/schedule.py BE/tests/test_backend_contracts.py docs/specs/03-agent-schedule-spec.md
git commit -m "test: cover schedule engine invariants"
```

## Self-Review

- Spec coverage: dependency-safe ordering, active predecessor scheduling, same-assignee hard overlap prevention, 1-hour bucket density guard, limited repair, strict LLM rerank fallback, and unchanged Risk/API/FE scope are all covered.
- Placeholder scan: this plan contains no placeholder markers or unspecified implementation steps.
- Type consistency: all referenced runtime types already exist in `BE/app/schemas.py`; new helpers are local to `BE/app/agents/schedule.py`.
