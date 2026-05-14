# Project Structure

이 저장소의 목표 구조입니다. 각 팀원과 AI 도구는 이 구조를 기준으로 파일을 만들고 수정합니다.

```text
brainrot-patent/
  README.md
  AGENTS.md
  CONTRIBUTING.md
  TASKS.md
  .env.example

  docs/
    PROJECT_BRIEF.md
    MVP_SCOPE.md
    ROLE_GUIDE.md
    API_CONTRACT.md
    AI_DEV_RULES.md
    PROMPT_GUIDE.md
    DEMO_SCRIPT.md
    TWO_WEEK_PLAN.md
    PROJECT_STRUCTURE.md

  examples/
    sample_inputs.md
    sample_response.json

  prompts/
    system_prompt.md
    claim_prompt.md

  frontend/
    README.md
    # Next.js app goes here

  backend/
    README.md
    # FastAPI app goes here

  tests/
    README.md
    # Playwright tests go here

  .github/
    pull_request_template.md
```

## 폴더별 책임

| 경로 | 책임 |
| --- | --- |
| `docs/**` | 기획, API, 일정, 발표 문서 |
| `examples/**` | 공통 테스트 입력과 샘플 응답 |
| `prompts/**` | LLM 시스템/청구항 프롬프트 |
| `frontend/**` | Next.js UI |
| `backend/**` | FastAPI, Agent, LLM 호출, PDF/fallback |
| `tests/**` | Playwright E2E 테스트 |
| `.github/**` | PR 템플릿과 GitHub 협업 설정 |

## 인터페이스 원칙

- Frontend는 Backend 응답을 `examples/sample_response.json`과 같은 구조로 기대합니다.
- Backend는 `docs/API_CONTRACT.md`의 요청/응답 구조를 유지합니다.
- AI/RAG는 Backend에 문자열이 아니라 구조화된 JSON을 넘기는 것을 목표로 합니다.
- Playwright는 발표용 입력 예시를 사용해 실제 사용 흐름을 검증합니다.

