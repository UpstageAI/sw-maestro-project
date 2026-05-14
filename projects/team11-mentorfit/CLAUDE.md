# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mentor-Fit is an AI-powered mentor recommendation system for AI/SW Maestro trainees. Given a team profile (3 members' skills, goals, mentoring needs), it recommends mentor candidates with structured reasoning — covering fit rationale, areas of help, gaps, and optimal multi-mentor combinations.

## Tech Stack

- **Backend API**: Python, FastAPI
- **LLM / Embeddings**: Upstage Solar API
- **Vector DB**: Qdrant or ChromaDB (semantic similarity search)
- **UI**: Streamlit
- **Pipeline**: LangGraph or sequential step pipeline
- **Local Storage**: SQLite or JSON
- **Data Source**: Notion API or CSV/Markdown export fallback

## Project Structure

```
mentor-fit/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── core/                    # Config, env, Solar API client
│   └── modules/
│       ├── data_collection/     # (planned) Notion ingestion, file parsers
│       ├── team_profile/        # (planned) Merge team members into unified profile
│       ├── mentor_candidate/    # 1st-round tag + semantic candidate search [implemented]
│       ├── combination_generator/ # (planned) Mentor combination generation
│       └── report/              # (planned) Recommendation report generation
├── data/
│   ├── sample/                  # Sample mentor/team data for local testing
│   └── cache/                   # Local cached profiles and results
├── docs/                        # Architecture and module specs
├── ui/
│   └── search_ui.py             # Streamlit search UI
└── tests/
```

See `docs/architecture.md` for the full pipeline design and component responsibilities.

## Development Commands

```bash
# Install dependencies (uv manages the venv automatically)
uv sync

# Run FastAPI dev server
uv run uvicorn app.main:app --reload

# Run Streamlit UI
uv run streamlit run ui/search_ui.py

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/path/to/test_file.py::test_function_name -v

# Run tests for a specific module
uv run pytest tests/modules/mentor_candidate/ -v
```

## Module Documentation

Each implemented module has a spec in `docs/`:

| Module | Spec |
|--------|------|
| `mentor_candidate` | `docs/mentor-candidate-module.md` |
| `combination_generator` | `docs/combination-generator-module.md` |
| `report` | `docs/report-module.md` |

## Upstage Solar API

Used for two purposes:
- **Embeddings**: Vectorize mentor bios and team profile for semantic similarity (`solar-embedding-1-large`)
- **Chat completions**: Combination generation and report generation (`solar-1-mini` or `solar-pro`)

API key is read from `UPSTAGE_API_KEY` environment variable.

## Commit Convention

Format: `(type)[(scope)]: (gitmoji) (short description)`

```
feat(mentor-candidate): ✨ add semantic re-ranking with Solar embeddings

기존 Jaccard 태그 점수만으로는 의미적 유사성을 반영하지 못해,
Solar 임베딩 기반 코사인 유사도를 추가해 combined_score를 산출하도록 변경.

BREAKING CHANGE: CandidateResult에 semantic_score 필드 추가 (nullable)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

- **scope**: 변경된 모듈명 (예: `mentor-candidate`, `tag-scorer`, `config`)
- **long description**: 왜 변경했는지 필요할 때만 추가
- **BREAKING CHANGE**: 인터페이스·스키마 변경 시 footer에 명시
- **Co-Authored-By**: 항상 포함

자주 쓰는 타입/이모지 조합:

| type | gitmoji | 용도 |
|------|---------|------|
| `feat` | ✨ | 새 기능 |
| `fix` | 🐛 | 버그 수정 |
| `docs` | 📝 | 문서 |
| `test` | ✅ | 테스트 추가·수정 |
| `refactor` | ♻️ | 기능 변경 없는 리팩터 |
| `chore` | 🔧 | 설정·빌드·패키지 |
| `chore` | 🗃️ | 데이터 파일 |
| `chore` | 🎉 | 프로젝트 최초 설정 |

## Constraints & Edge Cases

- If Notion API access fails, fall back to CSV/Markdown export files in `data/` — the pipeline must handle both input paths
- If a mentor's bio or tags are sparse, lower their score and flag as "추가 확인 필요" in output — never infer or fabricate data
- The matched-mentor exclusion list may be stale; surface a warning in the report rather than silently excluding
- AI recommendations are reference material only; final mentor selection and outreach are always done by the user
