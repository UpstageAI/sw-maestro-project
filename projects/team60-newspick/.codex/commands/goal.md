---
description: Set, inspect, or complete the active Codex goal for this thread.
argument-hint: [objective | status | complete]
---

# ./goal

Use Codex's goal tools to manage the current thread goal.

The user invoked this command with: $ARGUMENTS

## Behavior

- If `$ARGUMENTS` is empty, `status`, `show`, or `check`, call `get_goal` and summarize the current active goal.
- If `$ARGUMENTS` is `complete`, `done`, or `achieved`, call `update_goal` with `status: complete` only when the active goal is actually achieved.
- Otherwise, treat `$ARGUMENTS` as the concrete objective and call `create_goal` with that objective.

## Notes

- Do not create a vague placeholder goal.
- Do not mark a goal complete just because work paused or the budget is low.
- If a goal already exists and the user provides a new objective, explain that the current goal must be completed before a new one can be created.
