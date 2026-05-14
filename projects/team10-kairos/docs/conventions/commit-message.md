# Commit Message Convention

## Format

Use Conventional Commits:

```text
<type>(<scope>): <subject>

<body>

<footer>
```

Only the first line is required.

## Allowed Types

| Type       | Use for                                             |
| ---------- | --------------------------------------------------- |
| `feat`     | User-facing feature                                 |
| `fix`      | Bug fix                                             |
| `docs`     | Documentation-only change                           |
| `style`    | Formatting-only change with no behavior impact      |
| `refactor` | Code restructuring with no intended behavior change |
| `test`     | Test additions or updates                           |
| `chore`    | Maintenance task                                    |
| `ci`       | CI configuration                                    |
| `build`    | Build system or dependency changes                  |

## Scopes

Prefer layer-based or domain-based scopes over platform scopes.

Recommended scopes:

- `frontend`
- `backend`
- `api`
- `parser`
- `schedule`
- `notification`
- `spec`
- `ci`

Use platform scopes only for platform-specific behavior:

```text
fix(android): handle notification permission request
fix(ios): fix calendar permission wording
```

## Subject Rules

- Use lowercase unless a proper noun is required.
- Use imperative, concise wording.
- Do not end with a period.
- Keep the first line focused on one change.

## PR Titles Are Different

Commit messages use Conventional Commits:

```text
feat(frontend): add schedule confirm card
```

PR titles use bracket style:

```text
[Feature] Add schedule confirm card
```

Do not mix the two formats.

## Enforcement

Use `commit-msg` hook locally and commitlint in CI.

Recommended local hook:

```text
.husky/commit-msg
```

Recommended CI workflow:

```text
.github/workflows/commitlint.yml
```
