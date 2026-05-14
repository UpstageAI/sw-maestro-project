# Ideation Context Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI MVP that ingests planning documents, stores raw sources/chunks/cards/relations in SQLite, supports deterministic retrieval and grounded Q&A, and exposes REST APIs plus a compact local UI.

**Architecture:** The app is split into focused modules: `core` for settings, `db` for SQLite connection and schema, `repositories` for persistence, `services` for parsing/chunking/extraction/retrieval/Q&A, `workflows` for storage and retrieval orchestration, `api` for FastAPI routers, and `web` for local pages. External LangGraph and LLM adapters are optional; missing remote configuration is reported explicitly so tests stay reproducible without API keys.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Pydantic, SQLite, pytest, httpx/TestClient, pypdf, pandas, optional ChromaDB.

---

## File Structure

- `app/main.py`: FastAPI application factory and route mounting.
- `app/api/`: HTTP routers for health, workspaces, documents, cards, search, and Q&A.
- `app/core/config.py`: Environment-based settings.
- `app/db/connection.py`: SQLite connection management and schema initialization.
- `app/models/schemas.py`: Pydantic request/response/domain schemas.
- `app/repositories/sqlite.py`: Persistence operations for all SQLite tables.
- `app/services/parsing.py`: `.txt`, `.md`, `.pdf`, and `.csv` parsing.
- `app/services/chunking.py`: Chunk splitting and low-value chunk filtering.
- `app/services/extraction.py`: Knowledge Card extraction with deterministic rules and validation.
- `app/services/embeddings.py`: Deterministic local embedding abstraction.
- `app/services/vector_store.py`: In-memory/persistent local vector index abstraction with optional Chroma-compatible boundary.
- `app/services/relations.py`: Candidate card relation detection.
- `app/services/retrieval.py`: Card/chunk search and one-hop relation expansion.
- `app/services/qa.py`: Stored-context-only answer generation.
- `app/workflows/storage.py`: Storage preprocessing flow.
- `app/workflows/qa.py`: Retrieval Q&A flow.
- `app/web/templates/`: Minimal HTML templates.
- `tests/`: Unit and API tests.
- `requirements.txt`: Runtime and test dependencies.
- `.env.example`: Local configuration reference.
- `README.md`: Setup, run, and sample workflow instructions.

## Task 1: Project Foundation

**Files:**
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/api/__init__.py`
- Create: `app/api/health.py`
- Create: `app/core/__init__.py`
- Create: `app/core/config.py`
- Create: `tests/test_health.py`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Modify: `README.md`

- [ ] **Step 1: Write failing health API test**

Create `tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Ideation Context Hub"}
```

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_health.py -q`

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Implement minimal app foundation**

Create FastAPI app factory, health router, settings defaults, dependency files, `.gitignore`, `.env.example`, and README setup instructions.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_health.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add .gitignore .env.example README.md requirements.txt app tests
git commit -m "feat: add fastapi project foundation"
```

## Task 2: SQLite Metadata Storage

**Files:**
- Create: `app/db/__init__.py`
- Create: `app/db/connection.py`
- Create: `app/models/__init__.py`
- Create: `app/models/schemas.py`
- Create: `app/repositories/__init__.py`
- Create: `app/repositories/sqlite.py`
- Create: `tests/test_repository.py`

- [ ] **Step 1: Write failing repository tests**

Cover workspace creation, raw document persistence, chunk persistence, card persistence, relation persistence, and chat history persistence with a temporary SQLite database.

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_repository.py -q`

Expected: FAIL because database and repository modules do not exist.

- [ ] **Step 3: Implement SQLite schema and repository**

Create tables for `workspaces`, `raw_documents`, `chunks`, `knowledge_cards`, `relations`, and `chat_history`. Store list fields as JSON text. Return typed dictionaries or Pydantic models consistently.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_repository.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/db app/models app/repositories tests/test_repository.py
git commit -m "feat: add sqlite metadata store"
```

## Task 3: Parsing, Chunking, And Extraction

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/parsing.py`
- Create: `app/services/chunking.py`
- Create: `app/services/extraction.py`
- Create: `tests/test_parsing_chunking_extraction.py`

- [ ] **Step 1: Write failing parser/chunker/extractor tests**

Test `.txt` and `.md` parsing from bytes, `.csv` parsing into readable text, chunk splitting by paragraphs, low-value chunk filtering, deterministic extraction of idea/hypothesis/evidence/risk/decision cards, and `needs_review` behavior for unstructured planning text.

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_parsing_chunking_extraction.py -q`

Expected: FAIL because service modules do not exist.

- [ ] **Step 3: Implement parsing, chunking, and deterministic extraction**

Implement extension-based parsing. Use pypdf for PDF text extraction. Use pandas for CSV. Create deterministic Korean/English keyword heuristics for MVP card extraction. Validate cards with Pydantic schema and use `needs_review` when no specific card type is detected.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_parsing_chunking_extraction.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/services tests/test_parsing_chunking_extraction.py requirements.txt
git commit -m "feat: add document parsing and extraction"
```

## Task 4: Storage Workflow And Ingestion API

**Files:**
- Create: `app/workflows/__init__.py`
- Create: `app/workflows/storage.py`
- Create: `app/api/workspaces.py`
- Create: `app/api/documents.py`
- Create: `tests/test_ingestion_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write failing ingestion API tests**

Test workspace creation, text document ingestion, raw document persistence, chunk count, card count, and unsupported file rejection.

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_ingestion_api.py -q`

Expected: FAIL because routers/workflows do not exist or are not mounted.

- [ ] **Step 3: Implement storage workflow and routes**

Wire repository, parser, chunker, extractor, and relation detector placeholders through `StorageWorkflow`. Add `POST /api/workspaces`, `GET /api/workspaces`, `POST /api/workspaces/{workspace_id}/documents/text`, and `POST /api/workspaces/{workspace_id}/documents/upload`.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_ingestion_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/workflows app/api app/main.py tests/test_ingestion_api.py
git commit -m "feat: add ingestion workflow api"
```

## Task 5: Retrieval, Relations, And Card APIs

**Files:**
- Create: `app/services/embeddings.py`
- Create: `app/services/vector_store.py`
- Create: `app/services/relations.py`
- Create: `app/services/retrieval.py`
- Create: `app/api/cards.py`
- Create: `app/api/search.py`
- Create: `tests/test_retrieval_cards_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write failing retrieval/card API tests**

Test deterministic similarity search, card listing filters, card detail with source references, relation candidate creation for duplicate/related cards, and `/api/workspaces/{workspace_id}/search`.

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_retrieval_cards_api.py -q`

Expected: FAIL because retrieval and card APIs do not exist.

- [ ] **Step 3: Implement embeddings, local vector search, relation detection, and card/search routes**

Use deterministic token-count embeddings and cosine similarity. Store searchable text through repository queries. Add one-hop relation expansion. Keep ChromaDB as an optional future adapter boundary without making tests depend on it.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_retrieval_cards_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/services app/api app/main.py tests/test_retrieval_cards_api.py
git commit -m "feat: add retrieval and card APIs"
```

## Task 6: Grounded Q&A Flow

**Files:**
- Create: `app/services/qa.py`
- Create: `app/workflows/qa.py`
- Create: `app/api/qa.py`
- Create: `tests/test_qa_api.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write failing Q&A tests**

Test answer generation from stored cards/chunks, insufficient-context response, evidence card IDs, evidence chunk IDs, confidence, missing evidence, and chat history persistence.

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_qa_api.py -q`

Expected: FAIL because Q&A modules do not exist.

- [ ] **Step 3: Implement Q&A workflow and API**

Retrieve cards and chunks, expand one-hop relations, generate a concise Korean answer only from retrieved context, and store chat history. Return the required PRD response shape.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_qa_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/services/qa.py app/workflows/qa.py app/api/qa.py app/main.py tests/test_qa_api.py
git commit -m "feat: add grounded qa workflow"
```

## Task 7: Local Web UI

**Files:**
- Create: `app/web/__init__.py`
- Create: `app/web/routes.py`
- Create: `app/web/templates/index.html`
- Create: `tests/test_web_ui.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write failing web UI test**

Test that `/` returns HTML containing workspace creation, text ingestion, card search, and Q&A form affordances.

- [ ] **Step 2: Verify red**

Run: `pytest tests/test_web_ui.py -q`

Expected: FAIL because web routes/templates do not exist.

- [ ] **Step 3: Implement minimal HTML UI**

Serve a compact local page with forms that call the REST API using browser JavaScript. Keep styling simple and functional.

- [ ] **Step 4: Verify green**

Run: `pytest tests/test_web_ui.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/web app/main.py tests/test_web_ui.py
git commit -m "feat: add local web ui"
```

## Task 8: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Create: `tests/test_prd_coverage.py`

- [ ] **Step 1: Write PRD coverage smoke test**

Test that main API routes are registered and core schema constants include required card types, statuses, confidence values, and relation types from the PRD.

- [ ] **Step 2: Verify red if coverage gaps exist**

Run: `pytest tests/test_prd_coverage.py -q`

Expected before fixes: FAIL if any PRD constant or route is missing.

- [ ] **Step 3: Fill documentation and fix coverage gaps**

Document setup, test, run, sample flow, supported files, remote unavailable behavior, optional environment variables, and API overview. Fix missing routes/constants if the coverage test reports any.

- [ ] **Step 4: Verify all tests and app startup**

Run:

```bash
pytest -q
python -m compileall app
python -c "from app.main import create_app; app=create_app(); print(len(app.routes))"
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

Run:

```bash
git add README.md .env.example app tests
git commit -m "docs: add setup guide and prd coverage"
```

## Completion Audit

Before marking the goal complete:

- Confirm Git history contains PRD and implementation commits.
- Confirm `docs/PRD.md` exists and matches the user-provided project plan.
- Confirm all PRD must-have items have code or documentation evidence.
- Confirm `pytest -q` passes.
- Confirm `python -m compileall app` passes.
- Confirm FastAPI app can be imported and exposes `/health`, `/api/workspaces`, ingestion, card, search, Q&A, and web routes.
- Confirm no paid API key is required for tests.
