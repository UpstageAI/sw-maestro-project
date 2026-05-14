# Streamlit Demo UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit prototype that lets a user enter a service idea, runs the existing two-persona cross-review graph, and renders a product-style review report.

**Architecture:** Keep LangGraph topology unchanged. Add a small runner service that lazily streams graph updates and exposes UI-friendly events, then make `app.py` responsible only for Streamlit state, layout, and rendering.

**Tech Stack:** Python 3.11, Streamlit 1.44.1, LangGraph 0.2.74, LangSmith environment tracing, existing Pydantic schemas.

---

### Task 1: Add Streamlit Pipeline Runner

**Files:**
- Create: `services/pipeline_runner.py`
- Test: `tests/test_pipeline_runner.py`

- [ ] Define `PipelineEvent` with `node_name`, `label`, `update_keys`, and `update`.
- [ ] Add helpers for sample input loading, persona card status, LangSmith status, and persona card regeneration.
- [ ] Wrap `graph.stream({"raw_input": raw_input}, stream_mode="updates")` behind `stream_pipeline(raw_input)`.
- [ ] Lazy-import `graph` inside `stream_pipeline` so Streamlit startup is light and environment variables are already loaded.
- [ ] Add tests for node labels, input composition, sample fallback, and event construction without calling the LLM.

### Task 2: Implement Product-Style Streamlit UI

**Files:**
- Modify: `app.py`

- [ ] Build a sidebar with persona card status, LangSmith status, project name, and developer details.
- [ ] Build a main "review request" form with service name, stage, review focus chips, and long text input.
- [ ] Convert form fields into one `raw_input` string for the existing graph.
- [ ] Stream execution events into a user-facing progress timeline.
- [ ] Store final pipeline state and event history in `st.session_state`.
- [ ] Render final results as report tabs: summary report, persona panel, first reactions, cross review, evidence/debug.

### Task 3: Add Streamlit Demo Launcher

**Files:**
- Create: `scripts/run_demo_streamlit.ps1`

- [ ] Set `LANGSMITH_TRACING=true` unless `-NoTrace` is used.
- [ ] Generate `LANGSMITH_PROJECT=persona-reviewer-demo-YYYYMMDD-HHmmss` automatically.
- [ ] Load `.venv\Scripts\streamlit.exe` and run `streamlit run app.py`.
- [ ] Print the selected LangSmith project before launching.

### Task 4: Verify

**Commands:**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\ruff.exe check app.py services tests scripts
.\.venv\Scripts\python.exe -c "import app; from services.pipeline_runner import get_langsmith_status; print('imports ok')"
```

Expected result: all tests pass, ruff reports no errors, and imports complete without starting the graph.
