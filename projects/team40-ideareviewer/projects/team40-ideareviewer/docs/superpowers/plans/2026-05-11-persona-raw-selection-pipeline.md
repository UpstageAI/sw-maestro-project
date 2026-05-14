# Persona Raw Selection Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a reproducible script that creates 10,000 raw candidates, narrows them to 1,000 balanced candidates, and selects 100 final raw personas from `nvidia/Nemotron-Personas-Korea`.

**Architecture:** Add one focused script under `scripts/` that owns loading, quality filtering, deterministic diversity selection, JSON writing, and summary generation. Add unit tests for pure scoring and selection helpers so the algorithm can be changed safely without hitting Hugging Face in tests.

**Tech Stack:** Python 3.11, `datasets`, `unittest`, JSON files under `data/personas`.

---

## File Structure

- Create `scripts/sample_hf_personas.py`: CLI and pure helper functions for filtering, tagging, selecting, summarizing, and writing raw persona JSON files.
- Create `tests/test_sample_hf_personas.py`: unit tests for helper behavior with in-memory rows.
- Output generated data:
  - `data/personas/raw_personas.pool_10000.json`
  - `data/personas/raw_personas.candidate_1000.json`
  - `data/personas/raw_personas.selected_100.json`
  - `data/personas/persona_selection_summary.json`

---

### Task 1: Pure Selection Helpers

**Files:**
- Modify: `scripts/sample_hf_personas.py`
- Test: `tests/test_sample_hf_personas.py`

- [ ] **Step 1: Write failing helper tests**

Create `tests/test_sample_hf_personas.py` with tests for age grouping, quality filtering, derived tags, quota selection, and summary counts.

- [ ] **Step 2: Run the failing test**

Run:

```powershell
python -m unittest tests.test_sample_hf_personas -v
```

Expected: import errors or missing function failures.

- [ ] **Step 3: Implement helper functions**

Implement these functions in `scripts/sample_hf_personas.py`:

```python
age_group(age: int | None) -> str | None
text_blob(row: dict) -> str
is_quality_row(row: dict) -> bool
occupation_group(occupation: str | None) -> str
has_digital_signal(row: dict) -> bool
review_axes(row: dict) -> list[str]
enrich_row(row: dict) -> dict
select_with_quotas(rows: list[dict], quotas: dict[str, int]) -> list[dict]
summarize_rows(rows: list[dict]) -> dict
```

Selection must dedupe by `uuid`, prefer rows with richer text and rarer diversity keys, and preserve deterministic order for identical scores.

- [ ] **Step 4: Run helper tests**

Run:

```powershell
python -m unittest tests.test_sample_hf_personas -v
```

Expected: PASS.

---

### Task 2: Hugging Face CLI

**Files:**
- Modify: `scripts/sample_hf_personas.py`

- [ ] **Step 1: Add CLI arguments**

Support:

```powershell
python scripts/sample_hf_personas.py --pool-size 10000 --candidate-size 1000 --selected-size 100 --seed 40
```

Also support `--max-source-rows` for smoke tests and `--output-dir data/personas`.

- [ ] **Step 2: Load source data**

Use `datasets.load_dataset("nvidia/Nemotron-Personas-Korea", split="train", streaming=True)` so the script does not need to download the full dataset first.

- [ ] **Step 3: Save outputs safely**

Write JSON with UTF-8 and `ensure_ascii=False`. Do not overwrite output files until all three stages and summary have been built successfully in memory.

- [ ] **Step 4: Run a local smoke test**

Run:

```powershell
python scripts/sample_hf_personas.py --pool-size 20 --candidate-size 10 --selected-size 5 --max-source-rows 500 --seed 40 --output-dir C:\tmp\persona-smoke
```

Expected: four JSON files are created under `C:\tmp\persona-smoke`.

---

### Task 3: Generate Requested Data

**Files:**
- Generate: `data/personas/raw_personas.pool_10000.json`
- Generate: `data/personas/raw_personas.candidate_1000.json`
- Generate: `data/personas/raw_personas.selected_100.json`
- Generate: `data/personas/persona_selection_summary.json`

- [ ] **Step 1: Run full extraction**

Run:

```powershell
python scripts/sample_hf_personas.py --pool-size 10000 --candidate-size 1000 --selected-size 100 --seed 40
```

Expected: script prints counts for pool, candidate, selected, and output path.

- [ ] **Step 2: Verify JSON counts**

Run:

```powershell
python -m unittest tests.test_sample_hf_personas -v
python -m json.tool data/personas/persona_selection_summary.json > $null
```

Expected: tests pass and summary JSON parses.

- [ ] **Step 3: Inspect summary**

Check that `pool.count == 10000`, `candidate.count == 1000`, and `selected.count == 100`. Confirm selected age distribution matches the 12/14/16/18/20/20 target unless the dataset lacks enough quality rows.

---

## Self-Review Notes

- Spec coverage: Tasks cover raw pool, 1,000 candidate set, 100 final selected set, summary generation, and verification.
- Placeholder scan: No implementation step relies on unspecified behavior; helper names and command lines are explicit.
- Type consistency: All helper names are defined in Task 1 and reused by CLI/data generation tasks.

