# Milestone Suggest v2 Design

## Goal

Improve `POST /v1/projects/{project_id}/milestones:suggest` so it produces useful Korean milestone drafts instead of relying on a single loose prompt.

The endpoint should support two product moments with one API contract:

- Initial setup: when tasks are empty or sparse, suggest broad deliverable checkpoints from the project goal, date range, and team context.
- Execution planning: when tasks exist, use task titles, timing hints, dependencies, and assignees as context for more practical milestone names and rationales.

The response contract stays unchanged:

```json
{
  "project_id": "...",
  "proposed_milestones": [
    { "name": "...", "due_date": "YYYY-MM-DD", "ai_rationale": "..." }
  ],
  "agent_meta": { "latency_ms": 2400, "tokens": 0 }
}
```

## Current Problem

The current route asks the LLM to generate 3 to 8 milestones with names, dates, and rationales in one step. This is too underspecified:

- The LLM decides count, dates, names, and rationale at the same time.
- Date quality can drift because the prompt only says dates must stay inside the project range.
- The fallback is two fixed milestones, so it ignores project duration and goal context.
- The prompt does not distinguish early setup projects from projects with real task data.

## Design

Use a slot-based hybrid approach.

The backend owns deterministic structure:

- Decide milestone count from project duration.
- Create due-date slots inside the project date range.
- Detect whether the request is in setup mode or execution mode.
- Clamp and validate all final dates.
- Assemble the final API response.

The LLM owns language:

- Generate Korean deliverable-centered milestone names.
- Generate concise PM-facing rationales.
- Use the provided slot indexes instead of inventing dates.

## Milestone Count Policy

The route computes a target count before the LLM call, then applies `max_milestones`.

| Project duration | Target count |
| --- | --- |
| 7 days or less | 2-3 |
| 8-21 days | 3-4 |
| 22-45 days | 4-5 |
| 46-90 days | 5-6 |
| Over 90 days | 6-8 |

The implementation uses the lower target when there are fewer than three useful tasks, and the higher target when there are three or more useful tasks.

## Slot Generation

Slots are generated before calling the LLM.

- The first slot should avoid day-one unless the project is very short.
- The final slot should land on `project.ends_at`.
- Middle slots should be distributed evenly.
- Every slot must be clamped to `[project.starts_at, project.ends_at]`.
- Duplicate dates should be avoided when duration is short.

Each slot should include:

```json
{
  "slot_index": 1,
  "due_date": "YYYY-MM-DD",
  "position": "early | middle | final"
}
```

## Mode Detection

Use setup mode when the snapshot has too little task detail to support execution planning.

Setup mode:

- No tasks, or very few task titles with little scheduling information.
- The LLM should produce broad deliverable checkpoints.
- Examples: requirements output, MVP output, validation output, release readiness.

Execution mode:

- Multiple tasks exist, especially if they include due dates, estimates, dependencies, assignees, or milestone IDs.
- The LLM should use task context to name milestones around real work packages.
- It should not expose task IDs in the response.

The API response remains the same in both modes.

## LLM Input Shape

The route should send a compact, structured payload instead of the full raw snapshot where possible.

Example:

```json
{
  "project": {
    "goal": "...",
    "starts_at": "YYYY-MM-DD",
    "ends_at": "YYYY-MM-DD",
    "timezone": "Asia/Seoul"
  },
  "mode": "setup_mode",
  "slots": [
    { "slot_index": 1, "due_date": "YYYY-MM-DD", "position": "early" },
    { "slot_index": 2, "due_date": "YYYY-MM-DD", "position": "middle" },
    { "slot_index": 3, "due_date": "YYYY-MM-DD", "position": "final" }
  ],
  "team_summary": {
    "member_count": 3,
    "roles": ["PM", "Frontend", "Backend"]
  },
  "task_summary": {
    "total": 0,
    "titles": []
  }
}
```

The system instruction should be explicit:

- Output JSON only.
- Return exactly one milestone per supplied slot.
- Do not invent members, tasks, dates, or external facts.
- Do not change due dates.
- Names must be deliverable-centered, not phase-centered.
- Avoid vague names such as `기획 단계` or `개발 단계`.
- Use concise Korean suitable for a PM approval screen.

## LLM Output Shape

The LLM should return slot-indexed language only:

```json
{
  "milestones": [
    {
      "slot_index": 1,
      "name": "요구사항 산출물 확정",
      "ai_rationale": "프로젝트 목표를 실행 가능한 범위로 고정해야 이후 일정 산정이 안정적입니다."
    }
  ]
}
```

The backend maps each `slot_index` back to the deterministic due date.

## Validation And Fallback

The backend should validate each LLM item:

- `slot_index` must match an existing slot.
- `name` must be non-empty and at most 80 characters.
- `ai_rationale` must be at most 400 characters.
- Duplicate names should be replaced or deduplicated.
- Missing slots should be filled with fallback items.

Fallback should use project goal context and generated slots.

Example fallback names:

- `{goal_keyword} 요구사항 산출물 확정`
- `{goal_keyword} 핵심 산출물 완성`
- `{goal_keyword} 검증 및 출시 준비`

If a clean goal keyword cannot be extracted, use neutral deliverable names:

- `요구사항 산출물 확정`
- `핵심 기능 산출물 완성`
- `검증 및 출시 준비`

## Caching

The current cache key only uses project ID, goal hash, and `max_milestones`.

For v2, the cache key should include the fields that affect slot generation and mode:

- project ID
- project goal hash
- project start date
- project end date
- `max_milestones`
- compact task signature

This prevents stale milestone suggestions when tasks or dates change.

## Testing

Backend contract tests should cover:

- Task-empty setup mode uses duration-based count and deterministic dates.
- Task-present execution mode sends task summary to the LLM.
- LLM dates are ignored; final dates come from slots.
- Invalid LLM JSON falls back to goal-aware deterministic milestones.
- Missing or duplicate slot indexes are repaired.
- Cache key changes when project dates or task signature changes.
- Response contract remains compatible with existing FE mapping.

No FE contract change is required for this design.
