# Pull Request Convention

## Target Branches

| Source branch   | Target branch                   |
| --------------- | ------------------------------- |
| `feature/*`     | `dev`                           |
| `fix/*`         | `dev`                           |
| `refactor/*`    | `dev`                           |
| `chore/*`       | `dev`                           |
| `docs/*`        | `dev`                           |
| `release/x.y.z` | `main`                          |
| `hotfix/*`      | `main`, then reflect into `dev` |

## Title Format

Use bracket style:

```text
[Feature] Add schedule confirm card
[Fix] Preserve timezone offset
[Docs] Update API contract
[Refactor] Split schedule parser service
[Chore] Add commitlint
```

Allowed labels:

- `[Feature]`
- `[Fix]`
- `[Docs]`
- `[Refactor]`
- `[Chore]`
- `[Test]`
- `[CI]`
- `[Build]`
- `[Hotfix]`
- `[Release]`

## Review Rules

- At least one peer approval is required.
- Self-merge without approval is forbidden.
- Resolve review conversations before merge.
- Re-request review after substantial changes.
- Keep PRs scoped to one task.

## Merge Rules

Use Squash and Merge into `dev`.

Use Merge Commit or fast-forward into `main` for release history.

Do not merge if:

- Required CI checks fail.
- The branch name is invalid.
- The PR title format is invalid.
- The change contains unrelated scope creep.
- Behavior changed without updating relevant docs or specs.

## PR Description Checklist

Use a short, practical description:

```md
## Summary

-

## Verification

-

## Docs / Specs

-
```

For behavior changes, update the relevant spec or explain why no spec update is needed.

## Review Agent Checklist

A review-only agent should check:

- Branch name follows `<prefix>/<lowercase-kebab-description>`.
- Commit messages follow Conventional Commits.
- PR target is `dev` unless release or hotfix.
- No direct work is intended for `main` or `dev`.
- `AGENTS.md`, `CONTRIBUTING.md`, and conventions are followed.
- Relevant CI, test, lint, or typecheck commands are documented or run.
- Scope creep is absent.

Review output should be grouped as:

- Blockers
- Major issues
- Minor issues
- Missing automation
- Suggested fixes
