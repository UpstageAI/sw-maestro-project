# Agent Working Rules

This file is the short operational rule set for AI agents working in this repository.
Detailed conventions live under `docs/conventions/` and `CONTRIBUTING.md`.

## Required Reading

Before making non-trivial changes, read:

- `CONTRIBUTING.md`
- `docs/conventions/git-workflow.md`
- `docs/conventions/branch-naming.md`
- `docs/conventions/commit-message.md`
- `docs/conventions/pr-rule.md`
- `docs/conventions/code-style.md`

If a nested `AGENTS.md` exists in the area being edited, follow it as well.

## Git Workflow Rules

- Use `dev` as the integration branch.
- Create normal work branches from `dev`.
- Never commit or push directly to `main` or `dev`.
- Open PRs from work branches into `dev`.
- Use `main` only for release-ready code.
- Use `release/x.y.z` when stabilizing a release.
- Use `hotfix/*` only for urgent production fixes from `main`; reflect hotfixes back into both `main` and `dev`.

If the current branch is `main` or `dev`, do not create commits unless the user explicitly requests it.

## Branch Naming

Allowed prefixes:

- `feature/`
- `fix/`
- `hotfix/`
- `chore/`
- `refactor/`
- `docs/`
- `release/`

Format:

```text
<prefix>/<lowercase-kebab-description>
```

Examples:

```text
feature/schedule-confirm-card
fix/timezone-offset
docs/update-api-contract
chore/add-commitlint
```

## Commit Rules

Use Conventional Commits:

```text
<type>(<scope>): <subject>
```

Allowed types:

- `feat`
- `fix`
- `docs`
- `style`
- `refactor`
- `test`
- `chore`
- `ci`
- `build`

Prefer layer-based scopes:

- `frontend`
- `backend`
- `api`
- `parser`
- `schedule`
- `notification`
- `spec`
- `ci`

## PR Rules

- All changes must be merged through PR.
- PRs into `dev` require at least one peer approval.
- Self-merge without approval is not allowed.
- `dev` uses Squash and Merge.
- `main` uses Merge Commit or fast-forward for release history.
- PR title format: `[Feature] ...`, `[Fix] ...`, `[Docs] ...`, `[Refactor] ...`, `[Chore] ...`.
- Do not mix PR title format with commit message format.

## Before Finishing a Task

- Check the current branch name.
- Check commit message format if creating commits.
- Run relevant lint, typecheck, and tests when available.
- Update docs/specs when behavior changes.
- Report any checks that could not be run.
