# SOMA Recommender

SOMA Recommender는 SW Maestro 연수생의 학습 이력과 관심사를 바탕으로 특강, 멘토링, 학습 콘텐츠를 추천하는 개인화 추천 프로젝트입니다.

브라우저 확장 프로그램이 SW Maestro 사이트의 수강/활동 이력을 수집하고, 백엔드 API가 이 데이터를 추천 에이전트에 전달해 사용자에게 적합한 콘텐츠와 추천 사유를 제공합니다.

## 주요 기능

- SW Maestro 학습 이력 페이지에서 사용자 활동 데이터 수집
- 수집된 이력 기반 관심사 요약 및 추천 요청 생성
- FastAPI 기반 추천 API 제공
- 추천 에이전트를 통한 후보 콘텐츠 랭킹 및 추천 사유 생성
- SW Maestro 특강/공지 데이터 동기화 및 임베딩 저장 구조 제공
- Chrome Extension 팝업을 통한 추천 결과 확인

## 프로젝트 구조

```text
team32-SOMA-Recommender/
├── soma-recommender-backend/
│   ├── apps/api/                 # FastAPI 추천 API와 강의 동기화 모듈
│   ├── packages/agent/           # 추천 에이전트 패키지
│   ├── packages/shared/          # 공유 패키지
│   ├── docs/                     # 동기화 및 검증 문서
│   ├── pyproject.toml
│   └── uv.lock
├── soma-recommender-extension/
│   ├── src/                      # Chrome Extension 소스 코드
│   ├── manifest.json
│   ├── package.json
│   └── package-lock.json
├── .gitignore
└── README.md
```

## 기술 스택

### Backend

- Python 3.11
- FastAPI
- uv workspace
- pytest
- ruff
- pyright
- PostgreSQL / pgvector
- Upstage Embedding API

### Extension

- JavaScript
- Chrome Extension Manifest V3
- ESLint
- Prettier

## 백엔드 실행 방법

```bash
cd soma-recommender-backend
uv sync
uv run --project apps/api fastapi dev apps/api/main.py
```

기본 API 서버 주소는 다음과 같습니다.

```text
http://localhost:8000
```

추천 API 엔드포인트:

```text
POST /v1/recommendations
```

헬스 체크 엔드포인트:

```text
GET /health
```

## 백엔드 테스트

```bash
cd soma-recommender-backend
uv run pytest
uv run ruff check .
uv run pyright
```

## 환경 변수

백엔드 루트의 `.env_share`를 참고해 `.env` 파일을 구성합니다. 실제 계정 정보와 API 키가 들어간 `.env` 파일은 커밋하지 않습니다.

주요 환경 변수는 다음과 같습니다.

```text
DATABASE_URL=postgresql://...
UPSTAGE_API_KEY=...
SWM_BASE_URL=...
SWM_LOGIN_URL=...
SWM_NOTICE_LIST_URL=...
SWM_USERNAME=...
SWM_PASSWORD=...
```

## Chrome Extension 실행 방법

```bash
cd soma-recommender-extension
npm install
npm run lint
npm run format:check
```

Chrome에서 확장 프로그램을 로드합니다.

1. Chrome 주소창에서 `chrome://extensions`로 이동합니다.
2. 우측 상단의 개발자 모드를 켭니다.
3. `압축해제된 확장 프로그램을 로드`를 선택합니다.
4. `soma-recommender-extension` 폴더를 선택합니다.

확장 프로그램은 기본적으로 로컬 백엔드 API를 호출합니다.

```text
http://localhost:8000
```

## 주의 사항

이 프로젝트는 SW Maestro 사이트의 로그인된 사용자 학습 이력을 기반으로 동작합니다. 따라서 확장 프로그램을 정상적으로 사용하려면 Chrome에서 SW Maestro 사이트에 먼저 로그인되어 있어야 합니다.

SW Maestro 계정이 없거나 로그인 세션이 없는 환경에서는 학습 이력 페이지 접근과 데이터 수집이 제한될 수 있으므로, 전체 기능을 재현하거나 실행하는 데 어려움이 있을 수 있습니다.

## 사용 흐름

1. 백엔드 서버를 실행합니다.
2. Chrome에 확장 프로그램을 로드합니다.
3. SW Maestro 학습 이력 페이지에 접속합니다.
4. 확장 프로그램이 페이지의 이력 데이터를 읽어 추천 API로 전달합니다.
5. 백엔드가 추천 에이전트를 실행하고 추천 결과를 반환합니다.
6. 사용자는 확장 프로그램 팝업에서 추천 콘텐츠와 추천 사유를 확인합니다.

## 참고 문서

- `soma-recommender-backend/README.md`
- `soma-recommender-backend/packages/agent/README.md`
- `soma-recommender-backend/docs/lecture_sync_db_test.md`
- `soma-recommender-backend/docs/lecture_sync_review_guide.md`
- `soma-recommender-extension/README.md`
