# Git Workflow Convention

## Purpose

This convention defines the repository branch flow and separates soft guardrails from hard guardrails.

- Soft guardrails: `AGENTS.md`, `CONTRIBUTING.md`, and convention documents
- Local guardrails: Git hooks, lint, typecheck, and tests
- Hard guardrails: GitHub branch protection and required CI checks

## Branch Flow

```text
main <- dev <- feature/*
           <- fix/*
           <- refactor/*
           <- chore/*
           <- docs/*
```

Release and emergency branches use this flow:

```text
main <- release/x.y.z
main <- hotfix/*
dev  <- hotfix/*
```

## Branch Roles

### `main`

`main` contains release-ready code only.

Rules:

- No direct push.
- No normal feature work.
- Only release or hotfix changes should target `main`.
- Releases are tagged with semantic version tags such as `v1.0.0`.

### `dev`

`dev` is the integration branch.

Rules:

- No direct push.
- Normal work branches target `dev`.
- PR approval and status checks are required.
- Use Squash and Merge for normal work branches.

### Work Branches

Work branches are short-lived and scoped.

Rules:

- Branch from `dev`.
- Target `dev`.
- Use the branch naming convention.
- Keep changes related to one task.

### `release/x.y.z`

Release branches stabilize code before merging to `main`.

Rules:

- Branch from `dev`.
- Target `main`.
- Accept only release stabilization changes, documentation updates, version updates, and critical fixes.
- After release, ensure `main` and `dev` are synchronized.

### `hotfix/*`

Hotfix branches are for urgent production fixes.

Rules:

- Branch from `main`.
- Target `main` first.
- Reflect the hotfix back into `dev`.
- Keep the scope as small as possible.

## Merge Policy

| Target | Source                                                  | Merge method                               |
| ------ | ------------------------------------------------------- | ------------------------------------------ |
| `dev`  | `feature/*`, `fix/*`, `refactor/*`, `chore/*`, `docs/*` | Squash and Merge                           |
| `main` | `release/x.y.z`                                         | Merge Commit or fast-forward               |
| `main` | `hotfix/*`                                              | Merge Commit or fast-forward               |
| `dev`  | `hotfix/*`                                              | Merge Commit, cherry-pick, or follow-up PR |

## Required Repository Settings

Protect both `main` and `dev`.

Required settings:

- Require pull request before merging.
- Require at least one approval.
- Dismiss stale approvals after new commits.
- Require status checks.
- Require conversation resolution.
- Disallow force pushes.
- Disallow deletion.

## Agent Checklist

Before editing:

- Check the current branch.
- If the branch is `main` or `dev`, do not commit unless explicitly requested.
- If the branch name is invalid, report it before continuing.

Before finishing:

- Run relevant checks.
- Update docs or specs when behavior changes.
- Report any skipped checks.
