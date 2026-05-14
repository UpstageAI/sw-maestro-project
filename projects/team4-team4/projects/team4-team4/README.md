# Brainrot Patent

황당한 아이디어를 실제 특허 명세서처럼 보이는 문서로 변환하는 AI 에이전트 데모 프로젝트입니다.

사용자는 "방구로 가는 자동차"처럼 일상어로 아이디어를 입력하고, 서비스는 특허 문서의 어투와 구조를 모사해 7개 섹션의 명세서 초안과 PDF 다운로드 결과물을 제공합니다.

## 2주 MVP 목표

- 한국어 입력 1~3문장을 받는다.
- 검색 또는 샘플 근거를 활용해 배경기술을 만든다.
- 특허 명세서 7개 섹션을 JSON으로 생성한다.
- 프론트엔드에서 결과를 미리보기로 보여준다.
- 최종 데모에서는 PDF 다운로드 또는 PDF 유사 화면까지 시연한다.

## 핵심 문서

- [Project Brief](docs/PROJECT_BRIEF.md)
- [MVP Scope](docs/MVP_SCOPE.md)
- [Role Guide](docs/ROLE_GUIDE.md)
- [API Contract](docs/API_CONTRACT.md)
- [AI Dev Rules](docs/AI_DEV_RULES.md)
- [Prompt Guide](docs/PROMPT_GUIDE.md)
- [Demo Script](docs/DEMO_SCRIPT.md)
- [Two Week Plan](docs/TWO_WEEK_PLAN.md)

## 팀 역할

| 번호 | 역할 | 담당 |
| --- | --- | --- |
| 1 | 발표, 기획 | 임준현 |
| 2 | Frontend | 박서연 |
| 3 | Backend & Agent | 이진중 |
| 4 | AI, RAG | 황현석 |
| 5 | Playwright | 추웅재 |

## 기술 스택 기준

- Frontend: Next.js 14, TypeScript, Tailwind CSS
- Backend: FastAPI, Python 3.11
- Agent: LangGraph 또는 단순 파이프라인
- Search/RAG: Tavily 또는 사전 샘플 데이터 기반 fallback
- PDF: WeasyPrint 또는 HTML print fallback

## 협업 시작 방법

팀원이 처음 pull한 뒤에는 아래 순서로 읽고 작업합니다.

1. `AGENTS.md`
2. `CONTRIBUTING.md`
3. `TASKS.md`
4. 본인 역할에 맞는 폴더 README

AI 코딩 도구에게 작업을 맡길 때는 `AGENTS.md`의 작업 요청 템플릿을 먼저 붙여넣습니다.

## 빠른 실행

Backend mock API:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend test:

```bash
python -m unittest discover -s backend/tests -t .
```

Scaffold check:

```bash
python scripts/validate_scaffold.py
```

Playwright:

```bash
cd tests
npm install
npx playwright test
```

## 현재 구현 상태

- `backend/app/main.py`: `/health`, `/api/generate` mock API
- `backend/app/generator.py`: `examples/sample_response.json` 기반 fallback 생성
- `frontend/app/page.tsx`: 입력/결과 미리보기 UI
- `tests/specs/demo-flow.spec.ts`: 발표용 입력 E2E 테스트 초안
- `.github/workflows/ci.yml`: scaffold와 backend unit test CI
