# 꼬리질문 — 기술 면접 꼬리 질문 생성기 (24조)

> LLM · RAG · LangGraph로 기술 면접 답변의 약점을 분석하고, 그 약점을 정조준한 꼬리 질문을 한 개씩 자동으로 이어가는 면접 코칭 시스템.

| 항목 | |
|---|---|
| 팀 | 소태호(팀장) · 원동규 · 이강식 · 임세현 · 최준원 |
| LLM | Upstage Solar Pro 3 (`solar-pro3`) |
| 임베딩 | Solar Embedding 1 Large (`solar-embedding-1-large`) |
| 백엔드 / 프론트엔드 | FastAPI + LangGraph / Next.js 14 (App Router) |

---

## 1. 프로젝트 소개

### 풀고 싶은 문제

기술 면접에서 **첫 질문보다 꼬리 질문에서 탈락**이 많다. 기존 도구는 미리 만들어둔 정적 질문 목록에 그치고, 혼자 준비하는 취준생은 본인 답변의 약점을 스스로 진단하기 어렵다. 우리는 다음 흐름을 한 묶음으로 자동화했다:

1. 사용자가 답변 → ② AI가 약점 한 곳을 식별 → ③ 그 약점을 정조준한 꼬리 질문 1개를 자동 생성 → ④ 같은 토픽이 충분히 다뤄지면 다른 토픽으로 자연스럽게 전환

### 어떤 가치를 주는가 — "내 자료, 내 답변에 맞춘 꼬리 질문"

정적 질문 목록이 아니라 **사용자가 실제로 한 답변**을 분석하고 본인이 업로드한 자료의 출제 패턴을 참고하여 면접관 관점에서 파고들 포인트를 찾아낸다.

### 주요 기능

| # | 기능 | 설명 |
|---|---|---|
| 1 | 이메일·비밀번호 인증 | bcrypt 해시 + JWT 7d. 사용자별로 세션·자료·이력 격리 |
| 2 | 자료 인입 (RAG) | md / pdf 업로드 또는 GitHub 레포 URL을 Chroma 벡터 DB에 인덱싱. 사용자별로 격리 |
| 3 | 첫 질문 자동 생성 | 트랙(CS / 기술 스택) + 도메인 / 키워드 + 자료를 기반으로 Solar가 면접관 톤의 첫 질문 생성 |
| 4 | 답변 분석 | answer_quality 3종 분류 (good / uncertain / incorrect) + 약점 노트 + "잘 모르겠어요" 입력 시 모범답안 자동 제공 |
| 5 | 꼬리 질문 생성 | 약점 노트를 정조준한 single probe 질문 (난이도 basic / intermediate / advanced) |
| 6 | 자동 도메인 전환 | 같은 도메인 follow-up이 3회 누적되거나 답변이 uncertain / incorrect면 다른 도메인으로 자연스럽게 pivot |
| 7 | SSE 스트리밍 UX | 분석 결과 + explanation + 다음 질문이 stage별로 실시간 typing |

### 대상 사용자

- IT/SW 직군 **기술 면접 준비자** (취준생 · 이직 준비자)
- CS 기초(OS · 네트워크 · DB · 자료구조) ~ 특정 기술 스택 (Spring · React 등) 면접 대비
- 혼자 준비하거나 스터디에서 **꼬리 질문의 질을 높이고 싶은** 사람
- 본인 정리 노트나 GitHub 면접 자료를 학습 루프에 직접 활용하고 싶은 사람

---

## 2. 기술 스택

### AI / 에이전트

| 영역 | 선택 | 선택 이유 |
|---|---|---|
| LLM | **Upstage Solar Pro 3** (`solar-pro3`) | 한국어 면접관 톤·구조화 출력(JSON Schema)·tool calling 일급 지원. 현지 latency 우수 |
| 임베딩 | **Solar Embedding 1 Large** (passage / query) | LLM과 같은 vendor라 단일 API 키 운용 |
| 에이전트 프레임워크 | **LangGraph** StateGraph + MemorySaver | 분기·병렬·HITL interrupt가 그래프 토폴로지로 명시되어 디버깅·시연이 직관적 |
| 벡터 DB | **Chroma** (파일 기반 SQLite) | 별도 외부 서비스 무필요 → 단일 호스트에 내장. v1.1에서 부담되면 Qdrant로 교체 가능 |
| 웹 검색 (선택) | **Tavily API** | LLM tool calling용 — RAG 자료가 빈약할 때 폴백 |

### 백엔드

| 영역 | 선택 | 선택 이유 |
|---|---|---|
| 웹 프레임워크 | **FastAPI** 0.115 | async 기본 + Pydantic 직결 + OpenAPI 자동 |
| 데이터 검증 | **Pydantic v2** | LangGraph 상태 + LLM 구조화 출력 + API 모델을 같은 타입 시스템으로 묶음 |
| 영속화 | **SQLAlchemy 2** (sync) + **SQLite** | 단일 호스트라 sync engine으로 충분, async 라우터에서 `asyncio.to_thread`로 격리 |
| 인증 | **JWT** (HS256, 7일) + **bcrypt** (cost=12) | 단일 vendor 종속 회피, 운영 단순화 |
| 외부 SDK | **openai** SDK | Solar API가 OpenAI-compatible — `langchain-upstage` 대신 한 단계 vendor lock-in 회피 |

### 프론트엔드

| 영역 | 선택 | 선택 이유 |
|---|---|---|
| 프레임워크 | **Next.js 14** (App Router) | 서버 사이드 rewrite로 백엔드 프록시 + 빠른 SSR |
| 스타일링 | **Tailwind** | utility-first 일관성 + AI-generic 그라데이션·이모지 회피 |
| 언어 | **TypeScript 5** | API 응답을 `lib/api.ts`에 1:1 타입 매핑해 BE↔FE 정합성 보장 |
| SSE 클라이언트 | fetch + ReadableStream 직접 파싱 (`lib/auth-fetch.ts`) | EventSource는 GET-only — POST에 SSE 응답 받으려면 reader 직접 다룸 |

---

## 3. LangGraph 워크플로우

```
                                  POST /sessions/seed
                                          │
                                          ▼
                                   generate_seed_question
                                  (Solar 1회 + 선택적 Tavily)
                                          │
                                          ▼
                            ┌─ 사용자가 답변 입력 ─┐
                            ▼                      │
              POST /sessions/stream (SSE)          │
                            │                      │
                            ▼                      │
   START                                           │
     │                                             │
     ├──▶ analyzer_node ────┐                      │
     │      (답변 분류:                             │
     │       good/uncertain/                       │
     │       incorrect + 약점)                     │
     │                       │  병렬 → 약 40% 단축  │
     └──▶ term_extractor ───┘                      │
                              ▼                    │
                    knowledge_retriever_node       │
                    (Chroma 검색 + Tavily 폴백)    │
                              │                    │
                              ▼                    │
                    question_generator_node        │
                    (단일 정조준 probe,            │
                     tool_calling max_iters=1)    │
                              │                    │
                              ▼                    │
                       evaluator_node              │
                       (품질 점수만 측정)           │
                              │                    │
                              ▼                    │
                       human_review (interrupt)    │
                              │                    │
                       ┌──────┴──────┐             │
                       ▼             ▼             │
                  awaiting_      complete ─────────┘
                  feedback        (도메인 자동 전환:
                                  same-domain 3회 후 또는
                                  answer_quality=uncertain/incorrect)
```

### 노드별 역할

| 노드 | 입력 | Solar 호출 | 출력 |
|---|---|---|---|
| `analyzer_node` | question + answer | 1× structured_chat | `AnalysisOutput` (quality + notes + 잘 모르겠어요 시 모범답안 + 질문 의도) |
| `term_extractor_node` | answer | 1× structured_chat (reasoning=low) | `TermOutput` (영/한 기술 용어) |
| `knowledge_retriever_node` | question + terms + analysis | 0 (Chroma 검색) + 조건부 Tavily | `retrieved_context: Chunk[]` |
| `question_generator_node` | analysis + retrieved_context + answer | 1× tool_calling (max_iters=1) + 1× structured_after_tools | `FollowUpOutput` (단일 probe) |
| `evaluator_node` | follow_ups + question + answer | 1× structured_chat (reasoning=low) | `EvaluationOutput` (점수) |
| `human_review_node` | (interrupt 이후 resume) | — | `feedback_count` increment |

### 속도 최적화

- `analyzer ∥ term_extractor` 병렬 fan-out (LangGraph 자동 join)
- Chroma 검색 결과가 충분하면 (`len ≥ 2 && score ≥ 0.4`) Tavily web fallback skip
- `tool_calling_chat`의 `max_iters: 2 → 1` (3곳 모두) — Solar 1회 round-trip 절감
- `/sessions/stream` SSE 엔드포인트 — 노드별 stage 이벤트 + explanation/question 텍스트 chunk 송출로 체감 응답 시간 추가 단축

---

## 4. 실행 방법

> Docker(권장) 와 로컬 직접 실행 두 가지 방식을 모두 지원한다. Docker 쪽이 의존성 격리·운영과 가까운 환경을 보장한다.

### 4.1 Docker로 로컬 환경 구성 (권장)

#### 사전 요구사항

| 도구 | 버전 | 설치 |
|---|---|---|
| Docker | 24+ (Compose v2 내장) | <https://www.docker.com/products/docker-desktop/> (Windows/macOS) · `apt install docker.io docker-compose-plugin` (Linux) |
| **Upstage Solar API 키** | — | <https://console.upstage.ai> 에서 발급. `up_...` 형태 |
| (선택) Tavily API 키 | — | <https://tavily.com>. RAG 자료 빈약 시 웹 검색 폴백용 |
| (선택) GitHub PAT | — | <https://github.com/settings/personal-access-tokens>. GitHub 레포 자료 인입 시 60→5,000회/h 상승 |

#### 1) 저장소 클론

```bash
git clone https://github.com/SoTaeHo/tail-question.git
cd tail-question
```

#### 2) 환경 변수 파일 준비

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local   # 선택 (mock 모드 사용 시)
```

`backend/.env`를 열어 최소한 `UPSTAGE_API_KEY` 를 채운다. `ALLOWED_ORIGINS=http://localhost:3000` 를 유지하면 docker-compose 환경에서 그대로 동작한다.

> Solar 호출 없이 UI만 확인할 거라면 `USE_MOCK_LLM=true` 로 시작해도 된다. 비용 0, 가짜 응답.

#### 3) 컨테이너 빌드 & 실행

```bash
# 개발 모드 (--reload + npm run dev). docker-compose.override.yml이 자동 적용됨
docker compose up --build

# 백그라운드로 띄우기
docker compose up --build -d

# 운영과 동일한 빌드(--reload 미적용, next start)로 띄우기
docker compose -f docker-compose.yml up --build -d
```

처음 빌드는 `chromadb`/`hnswlib` C 확장 컴파일 때문에 3 ~ 5분 정도 걸린다. 이후에는 의존성 캐시가 재사용되어 30초 내외.

#### 4) 동작 확인

| 대상 | URL | 기대값 |
|---|---|---|
| Backend health | <http://localhost:8000/health> | `{"status":"ok","boot_id":"..."}` |
| Frontend | <http://localhost:3000> | `/login`으로 리다이렉트 |
| Backend → Frontend rewrite | 프론트엔드 내부에서 `/api/backend/*` | 200 (compose DNS로 `backend:8000` 해석) |

`docker compose ps` 로 `tq-backend` 가 `healthy` 가 될 때까지 기다리면 `tq-frontend` 가 자동으로 기동된다 (`depends_on: service_healthy`).

#### 5) 자주 쓰는 명령어

```bash
docker compose logs -f backend          # backend 실시간 로그 (stage emoji 로그 그대로)
docker compose logs -f frontend         # Next.js dev 서버 로그
docker compose exec backend bash        # 컨테이너 안으로 진입
docker compose exec backend python -m app.scripts.migrate_users   # 레거시 사용자 마이그레이션 등
docker compose down                     # 정지 + 네트워크 정리 (볼륨은 유지)
docker compose down -v                  # 볼륨까지 삭제 — SQLite/Chroma 초기화 시
docker compose build --no-cache backend # 의존성 변경 후 강제 재빌드
```

#### 6) 볼륨 & 데이터 영속화

`docker-compose.yml` 이 호스트 디렉토리를 마운트해 컨테이너 재기동 후에도 데이터가 유지된다.

| 호스트 경로 | 컨테이너 경로 | 용도 |
|---|---|---|
| `./data/` | `/app/data` | SQLite DB (`tail_question.db`) — 사용자·세션·턴 |
| `./.chroma/` | `/app/.chroma` | Chroma 벡터 컬렉션 (사용자별 격리) |
| `./.materials/` | `/app/.materials` | 업로드된 md/pdf 원본 |

#### 7) 운영과의 차이 — `docker-compose.override.yml`

로컬 개발 시 자동으로 합쳐지는 override가 다음을 바꾼다:
- backend: `uvicorn --reload` + `./backend/app` 호스트 바인드 마운트 → 코드 수정 즉시 반영
- backend: 포트 바인드를 `0.0.0.0:8000` 로 풀어 호스트 브라우저에서 접근 가능
- frontend: `npm run dev` + `./frontend` 바인드 마운트, `node_modules`/`.next` 는 익명 볼륨으로 보호

운영 빌드(`docker compose -f docker-compose.yml up`)에서는 override가 무시되어 127.0.0.1 바인딩 + 빌드된 정적 자원만 서빙된다 (EC2 nginx 앞단 가정).

#### 8) 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `backend` 가 health check 실패하며 재기동 반복 | `backend/.env` 누락 또는 `UPSTAGE_API_KEY` 미설정. `docker compose logs backend` 로 401/SOLAR 에러 확인 |
| 빌드 시 `hnswlib` / `chroma-hnswlib` 컴파일 에러 | Docker Desktop의 메모리 한도(기본 2GB)에서 OOM. Settings → Resources에서 4GB+ 로 상향 |
| 프론트에서 `/api/backend/*` 호출이 502 | `BACKEND_URL` 이 `next build` 시점에 박힘. `frontend` 만 재빌드: `docker compose build --no-cache frontend` |
| Windows에서 변경한 코드가 reload 되지 않음 | WSL2 백엔드 사용 시 `CHOKIDAR_USEPOLLING=true` 를 `frontend` 환경 변수에 추가하거나 코드 트리를 WSL 파일시스템(`\\wsl$\...`)에 두기 |
| 포트 충돌 (`8000` / `3000` already in use) | 호스트의 기존 프로세스 종료 또는 override에서 포트 매핑 변경 (`"8001:8000"` 등) |
| Chroma 벡터 검색 결과가 비어 있음 | `./.chroma` 볼륨이 사용자 컬렉션을 캐싱하지 못함. `docker compose down -v` 후 자료를 다시 인입 |

---

### 4.2 로컬 직접 실행 (Docker 없이)

#### 사전 요구사항

| 도구 | 버전 | 설치 |
|---|---|---|
| Python | 3.11 또는 3.12 | (3.14는 chromadb의 PyO3 호환 한계로 미지원) |
| **uv** (Python 패키지 매니저) | 0.4+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20 또는 22 | <https://nodejs.org> |
| **Upstage Solar API 키** | — | <https://console.upstage.ai> 에서 발급. `up_...` 형태 |
| (선택) Tavily API 키 | — | <https://tavily.com>. RAG 자료 빈약 시 웹 검색 폴백용 |
| (선택) GitHub PAT | — | <https://github.com/settings/personal-access-tokens>. GitHub 레포 자료 인입 시 60→5,000회/h 상승 |

#### Backend (port 8000)

```powershell
cd backend
uv venv --python 3.12 .venv
.\.venv\Scripts\activate                        # macOS/Linux: source .venv/bin/activate
uv pip install -e .

cp .env.example .env                            # 그 다음 .env 편집:
```

`.env` 필수·선택 항목:

```dotenv
UPSTAGE_API_KEY=up_xxxxxxxxxxxxxxxxxxxx          # 필수
SOLAR_MODEL=solar-pro3                           # 기본값
USE_MOCK_LLM=false                               # true → LLM 호출 안 함 (비용 0, 가짜 응답)
ALLOWED_ORIGINS=http://localhost:3000

# RAG/검색 (선택)
TAVILY_API_KEY=tvly-dev-xxxxxxxxxxxx
USE_WEB_SEARCH=true
ENABLE_LLM_TOOL_CALLING=true
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# 인증 (비우면 부팅마다 새 secret. dev에서는 OK)
JWT_SECRET=
```

서버 띄우기:
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

검증: `curl http://127.0.0.1:8000/health` → `{"status":"ok",...,"boot_id":"..."}`.

#### Frontend (port 3000)

```powershell
cd frontend
npm ci
npm run dev
```

브라우저로 <http://localhost:3000> → `/login`으로 자동 이동 → 회원가입 후 사용.

> **Mock 전용 UI 작업**: 백엔드 없이 UI만 검증하려면 `frontend/.env.local` 에 `NEXT_PUBLIC_USE_MOCK=true` 를 추가하고 `npm run dev`. 모든 API 호출이 로컬 mock 데이터로 응답.

#### 시연 / 디버깅용 stage 로그

`backend/app/log_format.py` 가 LangGraph 노드 진입·종료, Solar 호출 시간, Tavily 검색 등을 emoji-marked 한 줄씩 출력한다.

```
🚀 [BOOT] tail-question backend 시작
✓  [BOOT] LangGraph 컴파일 완료
👤 [AUTH] register attempt | email='user@example.com'
✓  [AUTH] register ok      | claimed_sessions=0
🌱 [SEED] request          | domains=['Spring'] keywords=[] materials=0
📡 [SOLAR] tool_calling start  | model='solar-pro3' max_iters=1
🌐 [TAVILY] search             | query='JPA 영속성 컨텍스트' max_results=3
⏱  [TAVILY] done               | hits=3 elapsed='1.70s'
⏱  [SOLAR] tool_calling done   | iters=1 elapsed='2.78s'
✓  [SEED] generated         | question='JPA의 영속성 컨텍스트가 무엇이며…'
📥 [SUBMIT] /sessions/stream
▶  [ANALYZER] start         | question='…' answer_len=8
▶  [TERMS] start
✓  [TERMS] done             | count=4 terms=[…]
✓  [ANALYZER] done          | quality=uncertain notes=1
▶  [RETRIEVER] start
✓  [RETRIEVER] done         | total=3 user=2 web=1
▶  [QGEN] start
✓  [QGEN] done              | first_text='방금 …'
▶  [EVALUATOR] start
✓  [EVALUATOR] done         | score=0.78 pass_threshold=true
📤 [SSE] done
```

---

## 5. API 개요

### 인증

| 메소드 | 경로 | 설명 |
|---|---|---|
| POST | `/auth/register` | `{email, password, displayName?}` → `{token, user}` |
| POST | `/auth/login` | `{email, password}` → `{token, user}` |
| POST | `/auth/logout` | 204 (stateless) |
| GET | `/auth/me` | Bearer 검증 → `{id, email, displayName}` |
| POST | `/auth/claim` | `{legacyUserId}` → `{claimed: int}` |

### 면접 흐름

| 메소드 | 경로 | 설명 |
|---|---|---|
| POST | `/sessions/seed` | 첫 질문 생성 (도메인/키워드/자료 입력) |
| POST | `/sessions` | 답변 제출 → 분석 + 다음 follow-up 생성 |
| POST | `/sessions/stream` | 동일하지만 SSE로 stage 이벤트 + explanation/question 텍스트 chunk 송출 |
| POST | `/sessions/{thread_id}/feedback` | (HITL B 비활성, accept만 사용) |
| GET | `/sessions` | 본 사용자의 세션 목록 |
| GET | `/sessions/{id}` | 단건 (소유권 검증) |
| PATCH | `/sessions/{id}` | 제목 변경 |
| DELETE | `/sessions/{id}` | 삭제 |

### 자료 인입 (per-user)

| 메소드 | 경로 | 설명 |
|---|---|---|
| POST | `/materials/upload` | md/pdf 업로드 (≤ 1MB / 10MB) |
| POST | `/materials/github` | `{repo_url}` → 비동기 인덱싱 |
| GET | `/materials` | 본 사용자의 자료 목록 |
| GET | `/materials/{id}` | 단건 (소유권 검증) |
| DELETE | `/materials/{id}` | 삭제 (Chroma collection drop) |

---

## 6. 디렉토리 구조

```
tail-question/
├── backend/
│   ├── app/
│   │   ├── main.py                       # FastAPI 앱 + lifespan
│   │   ├── config.py                     # pydantic-settings 환경변수
│   │   ├── log_format.py                 # 시연용 stage 로거
│   │   ├── api/
│   │   │   ├── auth.py                   # /auth/* 엔드포인트
│   │   │   ├── sessions.py               # /sessions, /sessions/stream
│   │   │   └── materials.py              # /materials/*
│   │   ├── auth/
│   │   │   ├── jwt.py                    # encode/decode_token (HS256)
│   │   │   └── deps.py                   # current_user FastAPI dep
│   │   ├── graph/
│   │   │   ├── workflow.py               # StateGraph 조립
│   │   │   ├── nodes.py                  # 5+1 노드 + seed 흐름
│   │   │   ├── prompts.py                # 한국어 시스템 프롬프트
│   │   │   ├── schema.py                 # Pydantic 모델
│   │   │   └── tools/
│   │   │       └── web_search.py         # Tavily wrapper
│   │   ├── services/
│   │   │   ├── session_store.py          # SQLAlchemy session/turn CRUD
│   │   │   ├── user_store.py             # bcrypt + claim_orphan_sessions
│   │   │   └── material_store.py         # per-user material CRUD
│   │   ├── ingestion/
│   │   │   ├── github.py                 # GitHub md crawler
│   │   │   └── pipeline.py               # md/pdf → chunks
│   │   ├── llm/
│   │   │   ├── solar.py                  # Solar API + tool_calling
│   │   │   └── embeddings.py             # Solar Embedding wrapper
│   │   └── storage/
│   │       ├── db.py                     # SQLAlchemy engine + init_db
│   │       ├── models.py                 # User · Session · Turn · Material
│   │       └── chroma.py                 # Chroma client + upsert/search
│   ├── scripts/
│   │   └── migrate_users.py              # legacy user_id → User row
│   ├── pyproject.toml
│   └── .env.example
│
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx                      # 홈 라우터 (token 체크 → /chat or /login)
    │   ├── login/page.tsx                # 로그인/회원가입 segmented
    │   ├── onboarding/page.tsx           # 트랙 → 도메인/키워드 (XOR)
    │   ├── materials/page.tsx            # 자료 관리
    │   ├── chat/page.tsx                 # 새 세션 시작
    │   └── chat/[sessionId]/page.tsx     # 기존 세션 hydration
    ├── components/
    │   ├── chat/                         # chat-shell · analysis-rail · sidebar 등
    │   ├── chrome/                       # top-nav · user-menu
    │   ├── materials/
    │   └── onboarding/
    ├── lib/
    │   ├── auth.ts                       # localStorage + identity-scoped 정리
    │   ├── auth-fetch.ts                 # Bearer 자동 부착 + 401 redirect
    │   ├── api.ts                        # 모든 비즈니스 API
    │   ├── api-auth.ts                   # /auth/* 클라이언트
    │   └── ...
    └── next.config.mjs                   # rewrite + proxyTimeout 120s
```
