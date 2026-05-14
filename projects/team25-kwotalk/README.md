# 교톡 (Kwotalk)

> **교통사고 과실비율·합의금, 이제 교톡에서.**
> 교통 관련 법률 상담에 특화된 RAG 기반 한국어 AI 에이전트.

법령·판례·합의 사례를 근거로 사용자의 교통사고 상황을 분류하고, 단계별 대응 가이드와 합의금 추정 구간까지 한 번에 안내한다. 모든 답변에는 인용 마커(`[1]`, `[2]` ...)가 붙어 출처 문서로 역추적이 가능하다.

---

## 풀고자 하는 문제

교통사고를 당한 일반인은 보통 다음과 같은 상황에 놓인다.

- **무엇부터 해야 하는지 모른다.** 사고 직후 보험사·경찰·병원 중 어떤 순서로 처리해야 하는지 정리된 가이드를 찾기 어렵다.
- **합의금 시세를 가늠하기 어렵다.** 비슷한 사례·판례를 찾으려면 변호사 상담 또는 유료 서비스가 필요하다.
- **법령·판례 검색은 진입장벽이 높다.** 도로교통법·교통사고처리특례법 조문을 일반 사용자가 직접 해석하기 어렵다.
- **일반 LLM은 환각이 위험하다.** 법률 도메인에서 출처 없는 답변은 잘못된 의사결정으로 이어진다.

교톡은 **교통 도메인으로 스코프를 한정**하고, **검색 결과(법령/판례/사례)에 인용을 강제**하는 LangGraph 기반 멀티 에이전트 파이프라인으로 이 문제를 풀어낸다.

## 지원 사건 유형 (case_type)

| enum | 한국어 | 합의금 추정 |
|---|---|---|
| `HIT_AND_RUN` | 뺑소니 | 제공 |
| `WRONG_WAY_DRIVING` | 역주행·중앙선침범 | 제공 |
| `DRUNK_DRIVING` | 음주운전 | 제공 |
| `PEDESTRIAN_ACCIDENT` | 보행자사고 | 제공 |
| `RECKLESS_DRIVING` | 난폭운전·안전운전위반 | 미제공 |
| `OUT_OF_SCOPE` | 교통 무관 | — (도메인 외 안내) |

도메인 외 질문은 명시적으로 거절하고, 분류 신뢰도가 낮으면(< 0.4) 되묻기(clarify)로 빠진다.

---

## 아키텍처

```
┌──────────────────────────┐        SSE (event-stream)        ┌────────────────────────────────────┐
│  Next.js 16 / React 19   │ ───── POST /chat ───────────────▶ │  FastAPI + LangGraph              │
│  (frontend)              │ ◀──── meta / token / state ─────  │  (backend)                        │
│                          │       done / error                │                                    │
│  - 세션 localStorage     │                                    │  classify → clarify              │
│  - SSE 스트리밍 파서      │                                    │           → retrieve (FAISS)     │
│  - 인용 마커 / 진행단계    │                                    │           → guide / settlement   │
│    노드 표시              │                                    │           → generate → post_check│
└──────────────────────────┘                                    │           ↘ fallback             │
                                                                │                                    │
                                                                │  Upstage Solar (mini / pro)       │
                                                                │  FAISS + sentence-transformers    │
                                                                └────────────────────────────────────┘
```

### LangGraph 파이프라인

```
classify ─┬─ case_type == "OUT_OF_SCOPE"           → fallback_no_domain → fallback → END
          ├─ classification_confidence < 0.4       → clarify → END
          └─ retrieve ─┬─ docs == []               → fallback_no_docs   → fallback → END
                       └─ guide → settlement → generate → post_check → END
```

| 노드 | 역할 |
|---|---|
| `classify` | 사용자 질의를 6개 `case_type` 중 하나로 분류 + 신뢰도 산출 (`solar-mini`) |
| `clarify` | 신뢰도가 임계(0.4) 미만이면 추가 정보 요청 질문 생성 |
| `retrieve` | FAISS 벡터스토어에서 법령·판례·사례 검색 (현재 mock — case_type 기반 dict) |
| `guide` | `data/guides.yaml` 룰 기반 단계별 대응 절차 |
| `settlement` | `사례` 문서의 `settlement_amount` 통계(min/median/max/sample_size) 산출 |
| `generate` | 컨텍스트 + 인용 마커를 포함한 최종 답변 생성 (`solar-pro`) |
| `post_check` | 인용 일치도·신뢰도 점수, 변호사 권유 여부 판정 |
| `fallback` | 도메인 외 / 검색 결과 0건 케이스의 안전한 거절 응답 |

### 상태 계약 (`backend/app/state.py`)

`LegalState` TypedDict 가 3 파트(LLM / 검색 / 로직)의 공용 인터페이스다. 주요 필드:

- 입력: `session_id`, `user_query`, `history`
- 분류: `case_type`, `classification_confidence`, `needs_settlement`
- 검색: `retrieved_docs[]` — `{doc_id, type ∈ {법령,판례,사례}, title, content, case_types, score, settlement_amount}`
- 답변: `answer_text`, `citations[]` — `{marker_idx, doc_id}`
- 후처리: `confidence_score`, `recommend_lawyer`, `situation_summary`, `fallback_reason`

### SSE 이벤트 프로토콜

`POST /chat` 은 `text/event-stream` 으로 다음 5종 이벤트를 흘려보낸다.

| event | data | 용도 |
|---|---|---|
| `meta` | `{ phase?, node? }` | 진행 중인 노드 표시 (프론트 진행 표시기) |
| `token` | `{ text? }` | LLM 토큰 스트리밍 |
| `state` | `{ node?, patch? }` | 그래프 상태 부분 업데이트 (retrieved_docs, citations 등) |
| `done` | `{}` | 정상 종료 |
| `error` | `{ message? }` | 오류 |

---

## 디렉터리 구조

```
team25-kwotalk/
├── backend/                     FastAPI + LangGraph + FAISS
│   ├── app/
│   │   ├── agents/              classify / clarify / retrieve / guide / settlement / generate / post_check / fallback
│   │   ├── api/                 main.py (FastAPI), sse.py (이벤트 직렬화)
│   │   ├── llm/                 solar_client.py (Upstage Solar)
│   │   ├── prompts/             classify/generate 시스템 프롬프트 + few-shot
│   │   ├── utils/               citation_extractor, keyword_fallback, prompt_loader
│   │   ├── graph.py             LangGraph StateGraph 조립
│   │   ├── state.py             LegalState 계약
│   │   ├── taxonomy.py          CaseType enum
│   │   ├── constants.py         CLARIFY_THRESHOLD, MAX_CONTEXT_DOCS, 모델명 …
│   │   └── config.py            환경 변수 / CORS
│   ├── build_vector_store.py    법령·판례 임베딩 → FAISS 인덱스 구축
│   ├── data/                    원자료, 인덱스 (git 미포함)
│   ├── law.json                 법령 시드 데이터
│   └── tests/                   pytest (classify / generate / citation / graph)
│
└── frontend/                    Next.js 16 + React 19 + Tailwind v4
    ├── app/
    │   ├── (demo)/chat/[id]/    채팅 세션별 동적 라우트
    │   │   └── _components/     ChatView / LLMChat / UserChat
    │   ├── _components/         AppSideBar / ChatInputBox / PromptChip / StartChat / ThemeToggle
    │   ├── _lib/chat.ts         SSE 파서, 세션 localStorage, 백엔드 호출
    │   ├── layout.tsx           Pretendard 폰트 + 사이드바
    │   └── page.tsx             홈(StartChat)
    └── public/fonts/            Pretendard variable
```

---

## 기술 스택

**Backend**
- Python 3.10+
- FastAPI / Uvicorn — HTTP + SSE
- LangGraph — 그래프 기반 에이전트 오케스트레이션
- Upstage Solar (`solar-mini` 분류, `solar-pro` 생성) via OpenAI 호환 클라이언트
- FAISS (`faiss-cpu`) + sentence-transformers — 벡터 검색
- pytest / pytest-asyncio

**Frontend**
- Next.js 16 (App Router) — ⚠️ 기존 Next.js와 API/규칙이 달라짐, `frontend/AGENTS.md` 참조
- React 19, TypeScript 5
- Tailwind CSS v4
- Pretendard (variable font, 로컬 호스팅)
- `react-markdown` + `remark-gfm` — 답변 렌더링
- `lucide-react` — 아이콘
- 세션 영속화: 브라우저 `localStorage` (서버 DB 없음)

---

## 빠른 시작

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows
pip install -r requirements.txt
cp .env.example .env               # UPSTAGE_API_KEY 설정

python build_vector_store.py       # FAISS 인덱스 구축
uvicorn app.api.main:app --reload --port 8000
```

엔드포인트:
- `GET /healthz`
- `POST /chat` — SSE 스트리밍
- `POST /chat/sync` — 디버그용 동기 응답

### 2. Frontend

```bash
cd frontend
pnpm install
pnpm dev                           # http://localhost:3000
```

백엔드 주소를 바꾸려면 `NEXT_PUBLIC_API_BASE_URL` 환경 변수 (기본 `http://localhost:8000`).

---

## 설계상의 주요 결정

- **도메인 스코프 한정.** 범용 법률 챗봇이 아니라 교통 5종 + OOS 거절. 분류 단계에서 `OUT_OF_SCOPE` 라벨을 명시적 노드로 처리해 환각 위험을 1차 차단.
- **인용 강제.** `generate` 단계 출력에 `[n]` 마커를 포함시키고, `post_check` 에서 마커와 `retrieved_docs` 의 매칭을 검증. 환각 시 신뢰도 점수 하락 → 변호사 권유로 우회.
- **결정형 폴백.** 검색 0건 / 도메인 외는 LLM 재호출 없이 사전 정의된 안내문을 반환 (`fallback_node`).
- **상태 분할 계약.** `LegalState` 키로 LLM/검색/로직 파트가 독립 개발 가능. 검색 파트가 mock 상태에서도 end-to-end 통합이 깨지지 않도록 설계.
- **SSE 우선.** 토큰 스트리밍 + 노드 진행 표시를 위해 LangGraph 이벤트를 그대로 SSE로 변환. 프론트는 `meta` 이벤트로 진행 단계 UI를 그린다.
- **세션 로컬 저장.** 초기 버전은 서버 세션 스토어 없이 `localStorage` 로 운영 → 인프라 경량화.

---
