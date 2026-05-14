# AGENTS.md

Behavioral guidelines for any AI coding agent working on this repository (Claude Code, Cursor, Codex CLI, etc.). `AGENTS.md` is a symlink to this file, so other agents load it automatically. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Project Context: llm-blind-date

Multi-Agent Dating Platform — **4-person team (1 frontend, 3 backend)**. Spec is the contract: see [docs/backend-specs/](docs/backend-specs/). The skeleton is in place; teammates fill in service/repository bodies in parallel.

## Stack (locked-in — do not change without team agreement)

- **Python 3.11–3.12** (3.13+ breaks `pydantic-core` wheels)
- **FastAPI** + **SQLAlchemy 2.0 async** + **SQLite (aiosqlite)** at `data/app.db`
- **Upstage Solar LLM ONLY** (NOT OpenAI). All LLM calls go through [app/core/solar_client.py](app/core/solar_client.py). Default model `solar-pro2`.
- **Simple FastAPI `Depends`** graph at [app/routers/dependencies.py](app/routers/dependencies.py). Do not reintroduce `dependency-injector`, Redis, or PostgreSQL — those were removed from the original scaffold on purpose.
- **`BackgroundTasks`** for the async 20-turn conversation loop.

## Layout

```
app/
├── main.py
├── core/                    # config, db session, lifespan (seeds Matchmaker), errors, Solar client
├── routers/                 # / + /health (live), /api/* (stubs)
│   └── dependencies.py      # repo → service Depends graph
├── services/                # business logic (TODO bodies for teammates)
├── repositories/            # SQLAlchemy data access (TODO bodies)
├── models/
│   ├── db/                  # SQLAlchemy ORM (spec §3)
│   ├── dtos/                # cross-layer dataclass DTOs
│   └── schemas/             # Pydantic Request/Response (spec §3)
├── prompts/                 # Agent / Matchmaker / Chemistry templates
└── utils/text_utils.py
```

## Team Ownership (3 backend devs)

| 담당 | FR | 주요 파일 |
|------|------|----------|
| **A · Agent** | 001, 002 | `services/agent_service.py`, `repositories/agent_repository.py`, `prompts/agent_prompt.py` |
| **B · Conversation** | 003, 004, 006 | `services/{conversation,job}_service.py`, `repositories/{conversation,message,job}_repository.py` |
| **C · Chemistry & Integration** | 005, 007, E2E | `services/chemistry_service.py`, `repositories/chemistry_repository.py`, `prompts/{chemistry,matchmaker}_prompt.py`, `tests/` |

When editing a file, respect ownership: if a change crosses domains, surface it instead of silently editing across boundaries.

## Conventions

- **3-layer pattern**: Pydantic Schema (router I/O) ↔ DTO (service/repo) ↔ SQLAlchemy ORM (DB). Schemas have `from_dto`/`to_dto`; never let ORM rows leak past the repository.
- **Error format** (spec §5): `{"detail": "..."}` + correct HTTP status. Services raise domain exceptions from [app/core/errors/error.py](app/core/errors/error.py); the handler maps them.
- **Response shape**: return raw Pydantic models. Do not wrap in `{message, statusCode, data}` envelopes.
- **Single LLM entry point**: every Solar call goes through `app.core.solar_client.chat_completion`. Don't import `openai` directly elsewhere.
- **Background tasks** open their own `async_session_factory()` session — request-scoped repositories from `Depends(get_db)` are already closed by the time the task runs. See [app/services/conversation_service.py:71-77](app/services/conversation_service.py#L71-L77).
- **JSON columns** on SQLite: `tags`, `good_points`, `concerns`, `metrics`, `result` are `TEXT` — `json.dumps` on insert, `json.loads` on read inside the repository.

## Interface Stability

Method signatures, DTO field names, and Pydantic schema field names in the skeleton are **shared contracts**. Changing them without team coordination breaks everyone's parallel work. If a signature must change, raise it explicitly and update all call sites in one PR.

## Run / Test

```bash
cp .env.example .env             # set UPSTAGE_API_KEY
poetry env use python3.11
poetry lock && poetry install --no-root
./start.sh                       # http://localhost:8000/docs
poetry run pytest -v
```

[tests/app/router/test_health.py](tests/app/router/test_health.py) green = skeleton OK.
