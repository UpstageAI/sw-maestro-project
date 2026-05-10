# HireProof

Privacy-first hiring review assistant that helps a recruiter or interviewer compare candidates against a job description while preserving explainability and reducing direct exposure to personal identifiers.

## Project overview

HireProof takes a job description, suggests evaluation criteria, ingests candidate resumes, masks obvious PII, and produces two complementary scores:

- JD fit score: how well the candidate matches the role criteria
- Alignment score: how well the candidate's claims are supported by observable artifacts such as GitHub activity

The current build is an MVP designed for demonstration and iterative validation. It focuses on making the evaluation flow visible and auditable rather than claiming perfect judgment quality.

## Problem we are solving

Early-stage candidate screening is often:

- inconsistent across reviewers
- weak on evidence traceability
- risky from a privacy perspective when resumes contain direct identifiers

HireProof tries to improve this by structuring the screening process into:

1. criteria generation from the JD
2. candidate ingestion and masking
3. score generation with evidence
4. audit logging for later inspection

## Core features

- JD-based suggested evaluation criteria
- Resume upload support for TXT, PDF, and DOCX
- PII masking for names, emails, phone numbers, and obvious resident-registration-like patterns
- Candidate evaluation with score + evidence
- GitHub public profile snapshot collection for evidence alignment
- Korean/English Streamlit UI
- SQLite-based persistence for jobs, candidates, evaluations, token mappings, and audit logs
- Mock mode and Upstage-backed LLM mode

## Tech stack

- Python 3.12
- FastAPI
- Streamlit
- SQLite
- LangGraph
- Requests
- Pydantic
- Upstage Solar model integration

## Project structure

```text
app/
  agent/      # chat workflow and orchestration
  api/        # FastAPI routes
  core/       # domain models
  db/         # SQLite repository
  scripts/    # demo seed scripts
  services/   # parser, masking, evaluator, GitHub, pipeline
  tests/      # unit tests
  ui/         # Streamlit app
data/
  demo_samples/   # sample JDs and candidates for demos
  uploads/        # local uploaded files
  artifacts/      # SQLite and checkpoints
```

## How it works

1. A recruiter enters a job title and job description.
2. The system generates suggested evaluation criteria.
3. The recruiter confirms or edits the criteria.
4. Candidates are added through uploaded resumes or pasted text.
5. The system masks identifiable information before LLM evaluation.
6. A JD fit score and an evidence alignment score are produced.
7. Evidence snippets and audit logs are stored for review.

## Local run

1. Create a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -e ".[dev]"
```

3. Run the Streamlit demo UI:

```bash
python -m streamlit run app/ui/streamlit_app.py
```

4. Run the FastAPI server if needed:

```bash
python -m uvicorn app.main:app --reload
```

## Environment setup

Create a local `.env` file from `.env.example` when using the Upstage-backed evaluator.

```bash
export HIREPROOF_EVALUATOR_MODE=upstage
export HIREPROOF_UPSTAGE_API_KEY=your_api_key_here
export HIREPROOF_UPSTAGE_MODEL=solar-pro3
export HIREPROOF_UPSTAGE_BASE_URL=https://api.upstage.ai/v1
```

If these variables are not set, local development can use mock mode.

## Test

```bash
python -m pytest
```

## Demo scenario

To preload sample data for demonstration:

```bash
python -m app.scripts.seed_demo --job-key backend
```

This populates the local SQLite database with:

- one backend job description
- suggested criteria for that role
- multiple sample candidates
- precomputed candidate evaluations

## Current limitations

- GitHub verification is heuristic and based on public profile/repository signals
- Scoring quality depends on prompt quality and available public evidence
- PII masking is rule-based rather than full NER-based anonymization
- HWP support and richer artifact sources are not implemented yet
- This MVP is intended as a screening aid, not an autonomous hiring decision maker

## Future work

1. Improve grounding and citation quality for evidence extraction
2. Strengthen Korean-specific PII/NER handling
3. Add richer portfolio and document ingestion
4. Refine ranking and reviewer feedback workflows
