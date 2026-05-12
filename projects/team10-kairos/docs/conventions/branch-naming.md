# Branch Naming Convention

## Format

```text
<prefix>/<lowercase-kebab-description>
```

The description must use lowercase letters, numbers, and hyphens only.

Recommended validation pattern:

```regex
^(feature|fix|hotfix|chore|refactor|docs|release)/[a-z0-9]+(-[a-z0-9]+)*$
```

For release branches, use:

```regex
^release/[0-9]+\.[0-9]+\.[0-9]+$
```

## Allowed Prefixes

| Prefix      | Purpose                                       |
| ----------- | --------------------------------------------- |
| `feature/`  | New feature                                   |
| `fix/`      | Bug fix                                       |
| `hotfix/`   | Urgent production fix from `main`             |
| `chore/`    | Build, config, package, or maintenance update |
| `refactor/` | Refactoring without intended behavior change  |
| `docs/`     | Documentation-only change                     |
| `release/`  | Release stabilization                         |

## Good Examples

```text
feature/schedule-confirm-card
fix/timezone-offset
docs/update-api-contract
refactor/schedule-service
chore/add-commitlint
release/1.0.0
```

## Bad Examples

```text
feature/ScheduleCard
feat/schedule-card
feature_schedule_card
feature/schedule card
fix/timezone_offset
release/v1.0.0
```

## Enforcement

Use both local and CI validation:

1. `pre-push` hook for fast local feedback.
2. GitHub Actions check for PR head branch validation.

Local hooks are not enough because they can be skipped or missing.
