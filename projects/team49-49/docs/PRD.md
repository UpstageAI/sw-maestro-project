# Ideation Context Hub PRD

## 1. Product Summary

**Service name:** Ideation Context Hub

**One-line product definition:** AI conversations, meeting notes, interview memos, PRDs, and exported collaboration documents are converted into searchable ideation knowledge so teams can later ask why an idea changed, why a decision was made, and what evidence supports it.

**Primary goal:** Build a local monorepo app with a FastAPI backend and React/shadcn frontend that ingests planning documents, preserves raw sources, extracts reusable Knowledge Cards, stores searchable chunks and card metadata, links related cards, and answers questions only from stored context with source evidence.

**MVP principle:** The product is not an idea generator. It is a context preservation and evidence retrieval hub for early-stage project teams.

## 2. Problem

Early project teams use many tools at once: ChatGPT, Claude, Cursor, Notion, meeting notes, interviews, mentoring feedback, and PRDs. Valuable ideas and decisions are produced continuously, but they remain scattered across personal sessions and separate documents.

This causes five recurring problems:

1. Teams cannot easily trace where an idea first appeared or how it changed.
2. Previously rejected or already discussed ideas are revisited from scratch.
3. Decision rationale disappears over time.
4. Verified evidence, assumptions, and guesses are mixed together.
5. Personal AI conversations fail to become reusable team knowledge.

## 3. Target Users

### Primary Users

SOMA teams, hackathon teams, capstone teams, early startup teams, and side-project teams that frequently revise ideas under short timelines.

### Personas

**Project leader**

- Manages meetings, mentoring, interviews, and PRD writing.
- Uses AI tools often.
- Needs to answer questions like "Why did we abandon this direction?" and "What evidence supported this feature?"

**Project member**

- Owns a feature or research area.
- Wants to share useful AI conversation outcomes with the team.
- Needs a clean way to turn long personal AI sessions into team-level planning assets.

**New team member**

- Joins after prior planning decisions have already happened.
- Needs to quickly understand current direction, rejected alternatives, and evidence.

## 4. Success Criteria

### MVP Validation Criteria

1. A user can run the project locally.
2. A user can upload or submit `.txt`, `.md`, `.pdf`, `.csv`, pasted MCP output, and source links for Notion, GitHub, Slack, Linear, and web sources.
3. Raw documents are preserved without modification.
4. Documents are split into searchable chunks.
5. Reusable planning information is extracted into Knowledge Cards.
6. Knowledge Cards are stored persistently.
7. Related, duplicate, contradictory, and supporting card candidates can be queried.
8. A user can search stored cards and chunks.
9. A user can ask a question and receive an answer with card IDs, source documents, and quoted evidence.
10. If evidence is insufficient, the system clearly says stored context is insufficient.

### Product Quality Metrics

- Card extraction approval target: at least 70 percent in sample review.
- Q&A response target: 8 seconds or less for small sample datasets.
- Conflict candidate precision target: at least 50 percent user acceptance.
- Extraction omission target: at most 30 percent on 5 meeting notes and 3 AI conversation samples.

### Verification Gates

Every product-facing change must pass the following checks before commit:

1. Backend and API regression suite: `python -m pytest`.
2. Frontend lint suite: `npm run frontend:lint`.
3. Frontend production build: `npm run frontend:build`.
4. Browser QA against `http://127.0.0.1:8000/` after FastAPI serves the latest `frontend/dist` assets.
5. Desktop and mobile viewport checks for no console errors, no horizontal overflow, and usable graph/search controls.

## 5. MVP Scope

### Must Have

1. Local FastAPI application.
2. React/shadcn browser UI served by FastAPI from the monorepo frontend build.
3. REST API endpoints for workspaces, document ingestion, card listing, search, relation inspection, and Q&A.
4. Raw document storage in SQLite.
5. Chunk storage in SQLite.
6. Knowledge Card storage in SQLite.
7. Card relation storage in SQLite.
8. Embedding-backed retrieval for chunks and cards.
9. Deterministic local vector retrieval for chunks and cards.
10. Deterministic local retrieval so the MVP can search without paid API keys.
11. LLM adapter abstraction for Upstage, Claude, and Codex/OpenAI OAuth bearer token.
12. Remote Q&A status handling so missing LangGraph configuration is shown explicitly instead of generating a local answer.
13. Pydantic validation for extracted Knowledge Cards.
14. Retry and graceful skip behavior for malformed LLM extraction output.
15. API documentation through FastAPI OpenAPI.
16. README with local setup, environment variables, and sample instructions.
17. LangGraph Studio-style graph inspection for workflow-oriented source/card/relation debugging.
18. Obsidian-style graph visualization for documents, cards, and one-hop relation links with search, groups, local graph depth, zoom, pan, drag, node sizing, and link distance controls.
19. Workspace and Knowledge Card CRUD: workspace rename/delete, manual card create from a typed evidence quote, full-field card update, and card delete. Workspace delete cascades to documents, chunks, cards, and relations through SQLite foreign keys.
20. Local LangGraph Studio is the canonical orchestration surface. `source_intake` runs on port `2025` and `qa_assistant` runs on port `2024`. Remote LangGraph deployment is optional and is not part of the demo path.
21. Retrieval ranks cards and chunks by score after metadata first-pass filtering (workspace, card type, status, source type), and slices the top-N for context. There is no fixed similarity threshold cutoff.
22. Quality Review surfaces per-card feedback: each review target carries `card_id`, `issue`, `suggestion`, and `priority`, so a reader can act on individual cards rather than a single workspace-wide summary.

### Nice To Have, Excluded From MVP

1. Scheduled background synchronization for connected sources.
2. Browser redirect OAuth with per-user refresh token storage.
3. Google Docs integration.
4. Team permission model.
5. Real-time collaboration.
6. Mobile UI.
7. STT-based meeting ingestion.
8. Advanced graph reasoning beyond bounded relation path exploration.
9. Advanced reranking or hybrid search.
10. Production authentication.
11. External vector database operation.

## 6. User Workflows

### Workflow 1: Ingest Scattered Planning Context

1. User creates or selects a workspace.
2. User uploads files, pastes connector output, or submits a direct source link with source metadata.
3. System stores the raw document.
4. System parses text from the file.
5. System chunks the document.
6. Agentic preprocessing filters low-value text.
7. System extracts Knowledge Cards for ideas, hypotheses, evidence, risks, decisions, feature candidates, target users, problems, and open questions.
8. System stores cards and indexes chunks/cards for retrieval.
9. System detects candidate relations to existing cards.

### Workflow 2: Review Idea Context

1. User opens the card list.
2. User filters by card type, status, confidence, tag, or keyword.
3. User opens a card and sees summary, source document, evidence quote, related cards, and relation candidates.
4. User can inspect why a card was created and where it came from.

### Workflow 3: Ask Evidence-Based Questions

1. User asks a question such as "Why did we switch from B2C to B2B2C?"
2. System analyzes the question intent.
3. System retrieves relevant Knowledge Cards and raw chunks.
4. System expands retrieved cards by one-hop relations.
5. Agent generates an answer using only the retrieved context.
6. Response includes conclusion, evidence cards, source documents, quotes, confidence, and missing evidence.
7. System stores Q&A history separately from long-term Knowledge Cards.

## 7. Agent Responsibilities

The Agent is an information storage and retrieval automation agent, not a final decision maker.

### Allowed Autonomous Actions

1. Parse uploaded documents.
2. Split documents into chunks.
3. Filter irrelevant or low-value chunks.
4. Extract candidate Knowledge Cards.
5. Generate keywords and tags.
6. Create candidate relations between cards.
7. Retrieve relevant cards and chunks for a question.
8. Generate evidence-based answers from stored context.
9. Mark low-confidence or malformed extraction results as needing review.

### Restricted Actions

1. The Agent must not modify uploaded raw documents.
2. The Agent must not delete cards automatically.
3. The Agent must not finalize planning decisions for the team.
4. The Agent must not present unsupported guesses as facts.
5. The Agent must not use external knowledge in Q&A answers unless a future product requirement explicitly permits it.

## 8. Knowledge Model

### RawDocument

Stores original source metadata and extracted text.

Required fields:

- `id`
- `workspace_id`
- `filename`
- `document_type`
- `source_type`
- `source_url`
- `external_id`
- `content`
- `created_at`

### Chunk

Stores searchable document fragments.

Required fields:

- `id`
- `document_id`
- `workspace_id`
- `chunk_index`
- `content`
- `token_estimate`
- `created_at`

### KnowledgeCard

Stores reusable planning knowledge.

Required fields:

- `id`
- `workspace_id`
- `source_document_id`
- `source_chunk_id`
- `card_type`
- `title`
- `summary`
- `evidence_quote`
- `keywords`
- `tags`
- `status`
- `confidence`
- `created_at`
- `updated_at`

Allowed `card_type` values:

- `idea`
- `problem`
- `target_user`
- `hypothesis`
- `evidence`
- `decision`
- `risk`
- `feature`
- `question`

Allowed `status` values:

- `proposed`
- `needs_validation`
- `validated`
- `rejected`
- `decided`
- `needs_review`

Allowed `confidence` values:

- `low`
- `medium`
- `high`

### Relation

Stores graph-like edges between Knowledge Cards in SQLite.

Required fields:

- `id`
- `workspace_id`
- `source_card_id`
- `target_card_id`
- `relation_type`
- `reason`
- `confidence`
- `created_at`

Allowed `relation_type` values:

- `supports`
- `contradicts`
- `duplicates`
- `related_to`
- `derived_from`

### ChatHistory

Stores Q&A interactions separately from long-term knowledge.

Required fields:

- `id`
- `workspace_id`
- `question`
- `answer`
- `referenced_card_ids`
- `referenced_chunk_ids`
- `created_at`

## 9. Functional Requirements

### Workspace API

- Create a workspace.
- List workspaces.
- Retrieve workspace detail.
- Update workspace name and description.
- Delete a workspace. Delete must cascade to its raw documents, chunks, knowledge cards, and relations through SQLite foreign keys.

### Ingestion API

- Accept uploaded files and direct text input.
- Accept pasted MCP/connector content and direct source links through a source ingestion endpoint.
- Automatically fetch Notion, GitHub, Slack, Linear, MCP, and web source links when the submitted content field is empty and the matching server token is configured.
- Support `.txt`, `.md`, `.pdf`, and `.csv`.
- Preserve `source_type`, `source_url`, and `external_id` for Notion, GitHub, Slack, Linear, MCP, web, and file uploads.
- Reject unsupported file types with clear error messages.
- Store raw source content before preprocessing.
- Return ingestion result with document ID, chunk count, card count, and skipped chunk count.

### Preprocessing Flow

The storage preprocessing flow must run in this order:

1. Parse source input.
2. Save raw document.
3. Split into chunks.
4. Filter low-value chunks.
5. Extract Knowledge Cards.
6. Validate cards with Pydantic.
7. Retry malformed model output once.
8. Store valid cards.
9. Store needs-review cards when extraction repeatedly fails.
10. Embed chunks and cards.
11. Detect relation candidates.

### Card API

- List cards.
- Filter cards by workspace, type, status, confidence, keyword, or tag.
- Retrieve card detail with source and relations.
- Create a card. When `source_document_id` and `source_chunk_id` are omitted, the API must create a manual source document and chunk from the evidence quote so every card stays traceable.
- Update card with full fields: `card_type`, `title`, `summary`, `evidence_quote`, `keywords`, `tags`, `status`, `confidence`. Workspace scope must be enforced.
- Delete a card. Card deletion cascades through SQLite foreign keys to dependent relations.
- Retrieve bounded multi-hop relation paths for a selected card.

### Search API

- Search Knowledge Cards.
- Search raw chunks.
- Apply metadata first-pass filtering (workspace, card type, status, confidence, source type) before scoring.
- Score-rank candidates by similarity and slice the top-N. Do not rely on a fixed similarity threshold.
- Tie-break on metadata closeness (same source type, same card type) before falling back to creation time.
- Use direct one-hop relations to enrich search results.

### Q&A API

- Accept a workspace ID and natural-language question.
- Retrieve relevant cards and chunks.
- Expand retrieved cards with one-hop relations.
- Generate an answer only from retrieved context.
- Return conclusion, evidence cards, source documents, evidence quotes, confidence, and missing evidence.
- Persist Q&A history separately from Knowledge Cards.
- Return an insufficient-context message when no relevant evidence is found.

### Web UI

The FastAPI app should serve the React/shadcn frontend with:

1. Workspace selector.
2. Multi-source ingestion form for Notion, GitHub, Slack, Linear, MCP output, direct links, and file upload.
3. Card list and filters.
4. Search box.
5. Q&A panel.
6. Answer display with card IDs and evidence.
7. LangGraph Studio-style graph view for step-by-step workflow inspection.
8. Obsidian-style graph view with zoom, pan, node drag, hover highlight, search filter, group toggles, local depth, display controls, force controls, document preview, and card relation path panel.

## 10. Technical Requirements

### Runtime

- Python 3.11 or later.
- FastAPI for API and local UI.
- Uvicorn for local server.
- SQLite for metadata persistence.
- Local deterministic vector retrieval for tests and no-key local runs.
- LangGraph-compatible workflow structure for storage and retrieval flows.
- Pydantic for schemas and validation.
- pypdf for text-based PDF parsing.
- pandas for CSV parsing.

### Project Structure

Expected high-level structure:

```text
app/
  main.py
  api/
  core/
  db/
  models/
  repositories/
  services/
  workflows/
  web/
frontend/
  src/
  components/
  dist/
tests/
docs/
package.json
requirements.txt
README.md
```

### Environment Configuration

Environment variables:

- `ICH_DATABASE_URL`
- `ICH_LLM_PROVIDER`
- `UPSTAGE_API_KEY` or `ICH_UPSTAGE_API_KEY`
- `ANTHROPIC_API_KEY` or `ICH_CLAUDE_API_KEY`
- `ICH_CODEX_OAUTH_TOKEN`
- `ICH_NOTION_TOKEN`
- `ICH_GITHUB_TOKEN`
- `ICH_SLACK_TOKEN`
- `ICH_LINEAR_TOKEN`
- `ICH_MCP_SERVER_URL`
- `ICH_MCP_ACCESS_TOKEN`

Supported `ICH_LLM_PROVIDER` values are `auto`, `upstage`, `claude`, `codex_oauth`, and `none`.
In `auto`, Upstage is selected only when an Upstage key exists; otherwise the LLM adapter returns no generated text.
Provider base URLs, default model names, source fetch timeout, MCP protocol version, embedding strategy, and local vector retrieval are code defaults so the environment surface stays small.
All external model configuration must be optional for local tests.

## 11. Non-Functional Requirements

### Reliability

- Raw documents must be saved before extraction starts.
- Failed chunk extraction must not stop the whole ingestion pipeline.
- Malformed model output must be retried once and then converted to a `needs_review` card or skipped with accounting.

### Traceability

- Every Knowledge Card must preserve source document and source chunk references.
- Every Q&A answer must include referenced card IDs or explain why none were found.

### Safety

- Uploaded raw documents must not be modified.
- The MVP must display or document a privacy warning for sensitive data.
- Email and phone masking can be offered as an option, but full privacy compliance is outside MVP scope.

### Testability

- Core parsing, chunking, extraction, search, relation detection, and Q&A unavailable-state behavior must be covered by automated tests.
- Tests must run without paid API keys.
- LLM and embedding providers must be replaceable with deterministic fakes.
- Frontend contract tests must verify that the React/shadcn shell, multi-source ingestion UI, LLM search UI, Graph Studio, and Obsidian Graph controls remain present.
- Browser QA must verify the real rendered app, not only static source contracts.

### Coaching Feedback Compliance

The 2026-05-10 coaching session set three policies that must be honored:

1. Retrieval result selection must use score-ranked top-N slicing on top of metadata first-pass filters. Static similarity thresholds are not acceptable for ranking decisions.
2. LangGraph orchestration during the demo must be shown through the local Studio (`source_intake` on port `2025`, `qa_assistant` on port `2024`). Remote LangGraph deployment paths must not be used as the primary demo surface, even when the SDK adapter exists.
3. Quality Review must surface per-card feedback (one issue and one suggestion per `card_id`). A single workspace-wide quality summary is not enough on its own.

### Browser QA Acceptance

The local browser acceptance pass must confirm:

1. Multi-source ingestion can accept pasted connector content and preserve `source_type`, `source_url`, and `external_id`.
2. Graph Studio renders source/card/relation links and node selection updates the inspector.
3. Obsidian Graph renders as a separate view with search, group toggles, zoom, pan, node drag, local graph depth, node size, and link distance controls.
4. Grounded LLM Search retrieves stored cards/chunks and returns evidence-backed answers.
5. Mobile width keeps the main flows reachable without horizontal overflow.

## 12. API Draft

### Workspace

- `POST /api/workspaces`
- `GET /api/workspaces`
- `GET /api/workspaces/{workspace_id}`
- `PATCH /api/workspaces/{workspace_id}`
- `DELETE /api/workspaces/{workspace_id}`

### Ingestion

- `POST /api/workspaces/{workspace_id}/documents/text`
- `POST /api/workspaces/{workspace_id}/documents/upload`
- `POST /api/workspaces/{workspace_id}/documents/source`
- `GET /api/workspaces/{workspace_id}/documents`

### Cards

- `GET /api/workspaces/{workspace_id}/cards`
- `POST /api/workspaces/{workspace_id}/cards`
- `GET /api/workspaces/{workspace_id}/cards/{card_id}`
- `PATCH /api/workspaces/{workspace_id}/cards/{card_id}`
- `DELETE /api/workspaces/{workspace_id}/cards/{card_id}`
- `GET /api/workspaces/{workspace_id}/cards/{card_id}/relations`
- `GET /api/workspaces/{workspace_id}/cards/{card_id}/paths`

### Search

- `GET /api/workspaces/{workspace_id}/search?q=...`
- `POST /api/workspaces/{workspace_id}/search/llm`

### Q&A

- `POST /api/workspaces/{workspace_id}/qa`
- `GET /api/workspaces/{workspace_id}/qa/history`

### Graph

- `GET /api/workspaces/{workspace_id}/graph`

### Health

- `GET /health`

## 13. Q&A Response Contract

A Q&A response must include:

```json
{
  "answer": "Stored-context-only Korean answer.",
  "confidence": "low | medium | high",
  "evidence_cards": [
    {
      "card_id": 1,
      "title": "Card title",
      "source_document": "meeting.md",
      "evidence_quote": "Original quote"
    }
  ],
  "evidence_chunks": [
    {
      "chunk_id": 1,
      "source_document": "meeting.md",
      "quote": "Original chunk excerpt"
    }
  ],
  "missing_evidence": ["Additional validation needed"]
}
```

If no relevant context exists, the response must say:

```text
현재까지 저장된 팀 컨텍스트에서는 관련된 논의나 근거를 찾을 수 없습니다.
```

## 14. Implementation Phases

### Phase 1: Project Foundation

- Initialize Git repository.
- Add project structure.
- Add settings, database connection, and test setup.
- Add README and environment example.

### Phase 2: Metadata Storage

- Add SQLite schema.
- Add repositories for workspaces, documents, chunks, cards, relations, and chat history.
- Add tests for persistence behavior.

### Phase 3: Parsing And Chunking

- Add text, markdown, PDF, and CSV parsing.
- Add chunking service.
- Add low-value chunk filter.

### Phase 4: Knowledge Extraction

- Add Pydantic card schema.
- Add deterministic extraction rules.
- Add LLM adapter interface.
- Add retry and needs-review behavior.

### Phase 5: Retrieval And Relations

- Add embedding abstraction.
- Add local deterministic vector store.
- Add card and chunk search.
- Add one-hop relation expansion.
- Add candidate relation detection.

### Phase 6: Q&A

- Add retrieval Q&A flow.
- Add grounded answer generator.
- Add chat history persistence.

### Phase 7: API And Web UI

- Add FastAPI routes.
- Add React/shadcn frontend under `frontend/`.
- Serve the frontend build through FastAPI.
- Add Graph Studio and Obsidian Graph views.
- Add API integration tests.

### Phase 8: Verification

- Run unit tests.
- Run API tests.
- Run frontend lint and production build.
- Run app startup check with the latest frontend build served by FastAPI.
- Run browser QA for Graph Studio, Obsidian Graph, multi-source ingestion, and Grounded LLM Search.
- Review PRD coverage.

### Phase 9: Demo Hardening (current branch)

- Workspace and Knowledge Card CRUD wiring across API, repository, schemas, and Inspector UI.
- `LLMCardExtractor` JSON-failure fallback to `DeterministicCardExtractor` so the sample data never collapses to `needs_review` cards.
- Retrieval ranking aligned with coaching feedback: metadata first-pass filter, score-ranked top-N slice, no fixed similarity threshold.
- Quality Review per-card issue / suggestion exposed in the Inspector panel.
- Demo data reset and `Load Samples` rerun before video capture so production cards are clean.

## 15. Open Decisions

The following decisions are fixed for MVP unless changed later:

1. FastAPI replaces the original Streamlit UI direction.
2. SQLite relation tables replace GraphDB.
3. Local deterministic vector retrieval replaces external vector DB setup for the current local MVP.
4. Upstage is the default remote LLM provider when configured, with Claude and codex_oauth adapters available by explicit provider selection.
5. LLM usage is optional in tests and local runs.
6. External integrations are excluded.
7. Workspace and Knowledge Card CRUD are inside scope for the demo. Workspace and card delete cascade through SQLite foreign keys, and manual card create writes a synthetic source document and chunk so traceability holds.
8. Obsidian-like graph visualization is included as a local UX surface.
9. SQLite relation path exploration is bounded to three hops for predictable local execution.
10. The repository is maintained as a backend/frontend monorepo.
11. LangGraph orchestration during the demo is shown through the local Studio. The remote LangGraph SDK adapter remains as an extension slot but is not part of the demo path.
12. Retrieval and search use score-ranked top-N slicing on top of metadata first-pass filtering. Static similarity thresholds are not used as the cut.
13. Quality Review must surface per-card feedback (issue and suggestion per `card_id`); a single workspace summary is not enough on its own.
14. When `LLMCardExtractor` cannot parse a JSON response, the storage flow falls back to the `DeterministicCardExtractor` for that chunk before recording a `needs_review` card. The `needs_review` card is reserved for the case when both extractors yield nothing usable.

## 16. Demo Readiness

Demo target was 2026-05-10 with a recorded video as deliverable. The current branch (`codex/notion-child-page-hops`) is in post-demo polish.

### Demo Surfaces

- Web app served by Vite on `http://127.0.0.1:5173`.
- FastAPI backend on `http://127.0.0.1:8000`.
- Local LangGraph Studio: `qa_assistant` on `http://127.0.0.1:2024`, `source_intake` on `http://127.0.0.1:2025`.

### Required Demo Walkthrough

The demo must show, in order:

1. Workspace selection and `Load Samples` to populate Notion / manual / web / GitHub fixtures.
2. Knowledge Card list with non-trivial card types (`decision`, `evidence`, `risk`, `hypothesis`, `feature`, `question`). The sample data must not collapse into `question/needs_review` cards.
3. Workspace rename / delete and manual Card create / update / delete from the Inspector panel.
4. Graph Studio and Obsidian Graph navigation with one-hop relations.
5. Local LangGraph Studio for `source_intake` and `qa_assistant`.
6. Grounded Q&A with cited evidence cards, chunks, relation evidence, and missing-evidence callouts.
7. Quality Review with per-card issue / suggestion entries.

### Known Demo-Blocking Risks

These are tracked outside `Implementation Phases` because they are state issues, not new scope:

1. `LLMCardExtractor` must fall back to `DeterministicCardExtractor` on JSON parse failure, otherwise sample ingestion produces only `question/needs_review` cards.
2. The frontend already calls workspace `PATCH` / `DELETE` and card `POST` / `PATCH` / `DELETE` endpoints. These endpoints must be merged into the demo branch; otherwise InspectorPanel actions return 404.
3. `frontend:lint` must be clean before recording. Cascading-render setState inside `NodeInspector` `useEffect` causes visible form flicker on card selection.
4. Demo SQLite (`data/ideation_context_hub.sqlite3`) must be reset before recording when LLM extraction has previously failed, so polluted `needs_review` rows do not appear in the recording.
