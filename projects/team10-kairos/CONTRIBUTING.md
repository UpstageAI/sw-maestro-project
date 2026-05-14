# Contributing Guide

This repository uses guardrails at three levels:

- Documentation guardrails: `AGENTS.md`, `CONTRIBUTING.md`, and `docs/conventions/*`
- Local guardrails: Git hooks, lint, typecheck, and tests
- Remote guardrails: GitHub branch protection and CI

Documentation tells people and agents what to do. Hooks, CI, and branch protection are the enforcement layer.

## Branch Strategy

```text
main <- dev <- feature/fix/refactor/chore/docs
```

### `main`

- Release-ready branch.
- Must always represent deployable code.
- Direct push is forbidden.
- Release tags use semantic versioning, for example `v1.0.0`.
- Release PRs normally come from `release/x.y.z`.
- Emergency production fixes may come from `hotfix/*`.

### `dev`

- Integration branch for normal work.
- Direct push is forbidden.
- All normal work branches target `dev`.
- Requires peer review and passing status checks before merge.

### Work Branches

- Created from `dev`.
- Merged back into `dev` through PR.
- Must use an allowed branch prefix.
- Keep the branch scoped to one feature, fix, refactor, chore, or documentation change.

## Branch Prefixes

| Prefix      | Purpose                                       |
| ----------- | --------------------------------------------- |
| `feature/`  | New feature                                   |
| `fix/`      | Bug fix                                       |
| `hotfix/`   | Urgent production fix from `main`             |
| `chore/`    | Build, config, package, or maintenance update |
| `refactor/` | Refactoring without intended behavior change  |
| `docs/`     | Documentation-only change                     |
| `release/`  | Release stabilization                         |

See `docs/conventions/branch-naming.md` for the full naming rule.

## Commit Messages

Use Conventional Commits:

```text
<type>(<scope>): <subject>
```

Examples:

```text
feat(frontend): add schedule confirm card
fix(api): preserve timezone offset
docs(spec): update reminder policy
chore(ci): add branch name lint workflow
```

Commit messages and PR titles intentionally use different formats. Do not mix them.

See `docs/conventions/commit-message.md` for allowed types and scopes.

## PR Rules

- General work branches target `dev`.
- `release/x.y.z` targets `main`.
- `hotfix/*` targets `main`, then must be reflected into both `main` and `dev`.
- Peer approval is required before merge.
- Self-merge without approval is forbidden.
- Resolve review conversations before merge.
- Merge work into `dev` with Squash and Merge.
- Merge release PRs into `main` with Merge Commit or fast-forward.

PR title format:

```text
[Feature] Add schedule confirm card
[Fix] Preserve timezone offset
[Docs] Update API contract
[Refactor] Split schedule parser service
[Chore] Add commitlint
```

See `docs/conventions/pr-rule.md` for details.

## Code Style

Follow `docs/conventions/code-style.md`.

For frontend work, also follow `frontend/AGENTS.md` and any conventions in `frontend/docs/conventions/`.

## Recommended Local Guardrails

Use Git hooks for fast local feedback. Husky is optional; native Git hooks are enough when the repository configures a versioned hooks path.

```text
.githooks/
  pre-commit      # eslint
  commit-msg      # commitlint, when configured
  pre-push        # branch name check, optional tests
```

Enable the versioned hooks once per clone:

```bash
git config core.hooksPath .githooks
```

Local hooks are helpful but bypassable with `--no-verify`, so important checks must also run in CI.

## Recommended CI Guardrails

Recommended workflows:

```text
.github/workflows/
  branch-name-lint.yml
  pr-title-lint.yml
  commitlint.yml
  lint.yml
  test.yml
```

| Workflow               | Purpose                         |
| ---------------------- | ------------------------------- |
| `branch-name-lint.yml` | Validate PR head branch names   |
| `pr-title-lint.yml`    | Validate PR title bracket style |
| `commitlint.yml`       | Validate commit messages        |
| `lint.yml`             | Run lint and formatting checks  |
| `test.yml`             | Run tests and type checks       |

## Recommended Branch Protection

Protect both `main` and `dev`.

Recommended settings:

- Require a pull request before merging.
- Require at least one approval.
- Dismiss stale approvals when new commits are pushed.
- Require required status checks to pass.
- Require conversation resolution before merging.
- Do not allow force pushes.
- Do not allow branch deletion.
- Restrict who can push directly.

`main` and `dev` are both hard guardrails. `dev` is the integration branch, so it must be protected with the same seriousness as `main`.
