# AI 노무사 (AI Labor Attorney)

> **사진 한 장으로 끝내는 근로계약서 검토.**
> Upstage Document Parse 로 계약서를 OCR 하고, 룰 엔진으로 최저임금·근로시간·휴게·주휴 4종을 즉시 점검한 뒤,
> LangGraph + 근로기준법 RAG 가 위험도 분석과 후속 Q&A 까지 책임지는 AI 노무 도우미입니다.

![Next.js 15](https://img.shields.io/badge/Next.js-15-black) ![React 19](https://img.shields.io/badge/React-19-149eca) ![TypeScript 5.8](https://img.shields.io/badge/TypeScript-5.8-3178c6) ![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688) ![LangGraph](https://img.shields.io/badge/LangGraph-Agent-1c3d5a) ![Upstage Solar](https://img.shields.io/badge/Upstage-Solar-7c3aed) ![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-ff6f61)

---

## 👋 팀 소개

| 항목 | 내용 |
|---|---|
| 팀 번호 | **Team 3** |
| 팀 이름 | **ailaborattorney** |
| 프로젝트 | AI 노무사 — 근로계약서 위반 자동 검토 + 근로기준법 RAG Q&A |
| 과정 | SW 마에스트로 / Upstage AI Lab |

---

## 🎯 풀고 싶은 문제

- 아르바이트·계약직·신입은 근로계약서를 받아도 **무엇이 위법한지 모릅니다.**
- 노무사 상담은 비싸고, 노동청 1350 은 진입장벽이 높으며, 검색 결과는 케이스에 맞지 않습니다.
- 그래서 **계약서 사진 1장 → 위반 항목 카드 → 후속 Q&A** 까지 60초 안에 끝나는 도구를 만들었습니다.

---

## ✨ 핵심 기능

| 단계 | 흐름 | 위치 |
|---|---|---|
| 1. 업로드 | PDF/이미지 드래그&드롭 → SQLite 메타 저장 | `frontend/app/api/upload` |
| 2. OCR | Upstage Document Parse (키 없으면 mock 폴백) | `frontend/lib/ocr/` |
| 3. 파싱 | 월급·주당시간·수습기간 등 `ContractData` 추출 | `frontend/lib/parser/` |
| 4. 룰 엔진 | 최저임금·근로시간·휴게·주휴 4종 검사 | `frontend/lib/rules/` |
| 5. AI 분석 | LangGraph 서버 호출(없으면 mock) → 위험도·권장 조치 | `frontend/lib/agent/` ↔ `backend/server.py` |
| 6. Q&A | 분석 컨텍스트 + 근로기준법 RAG 기반 질의응답 | `frontend/app/api/qa` ↔ `backend/server.py` |

UI 는 토스(TDS) 디자인 시스템을 참고한 컬러 팔레트 · Pretendard 폰트 · 큰 라운드 카드/CTA 로 구성했습니다.

---

## 🏗 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  frontend/  (Next.js 15 · App Router · TS · Tailwind 4) │
│                                                         │
│   [업로드] → /api/upload  ─────────► SQLite (better-sqlite3) │
│      │                                                  │
│      ▼                                                  │
│   [분석]   → /api/analyze ─► OCR(Upstage) ─► Parser ─► Rules │
│                                          │              │
│                                          └─► LangGraph 호출 │
│                                                  │      │
│   [Q&A]    → /api/qa     ────────────────────────┤      │
└──────────────────────────────────────────────────┼──────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────┐
│  backend/  (FastAPI · LangGraph · Upstage Solar)        │
│                                                         │
│   /qa         qa_graph        ─► ChromaDB(근로기준법)    │
│   /analyze    analyze_graph   ─► ChromaDB(근로기준법)    │
│                                                         │
│   임베딩: solar-embedding-1-large-query                  │
│   추론  : solar-pro                                      │
└─────────────────────────────────────────────────────────┘
```

> **Mock 폴백 설계**: `UPSTAGE_API_KEY` 또는 `LANGGRAPH_URL` 이 비어있거나 실패해도 frontend 가 자동으로 `lib/ocr/mock.ts`, `lib/agent/mock.ts` 응답으로 폴백합니다.
> 키가 없는 환경에서도 데모 흐름이 끊기지 않습니다.

---

## 🧱 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 15 (App Router) · React 19 · TypeScript 5.8 · Tailwind CSS 4 |
| 데이터  | SQLite + better-sqlite3 (계약서 메타 / Q&A 로그) |
| Backend | Python · FastAPI · Uvicorn |
| LLM 오케스트레이션 | LangGraph (qa_graph / analyze_graph 2-그래프 구조) |
| LLM / 임베딩 | Upstage Solar (solar-pro) · solar-embedding-1-large-query |
| 벡터 DB | ChromaDB (근로기준법 청크 임베딩, 사전 빌드 zip 동봉) |
| OCR | Upstage Document Parse |
| 패키지 매니저 | pnpm 9 (frontend), pip + venv (backend) |

---

## 🚀 빠른 시작

### 0. 사전 요구사항

- Node.js **22+** · pnpm **9+** (`corepack enable` 권장)
- Python **3.10+**
- Upstage API Key — https://console.upstage.ai (Document Parse + Solar)

### 1. 백엔드 (FastAPI + LangGraph)

```bash
cd backend
unzip -o chroma_db.zip -d .                    # ./chroma_db/ 생성 (≈2.4MB)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                           # UPSTAGE_API_KEY 입력
uvicorn server:app --port 8000 --reload        # http://localhost:8000
```

확인:

```bash
curl -s http://localhost:8000/ | jq
curl -s -X POST http://localhost:8000/qa \
  -H 'content-type: application/json' \
  -d '{"question":"해고 예고는 며칠 전에 해야 하나요?"}' | jq
```

### 2. 프론트엔드 (Next.js)

```bash
cd frontend
pnpm install
cp .env.example .env                           # UPSTAGE_API_KEY, LANGGRAPH_URL 입력
pnpm db:init                                   # SQLite 초기화 (data.db 생성)
pnpm dev                                       # http://localhost:3000
```

`.env`:

```env
UPSTAGE_API_KEY=                              # Upstage Document Parse (OCR)
LANGGRAPH_URL=http://localhost:8000           # 위에서 띄운 백엔드 주소
```

| 키 | 비워두면 |
|---|---|
| `UPSTAGE_API_KEY` | OCR 이 `lib/ocr/mock.ts` 로 폴백 (샘플 계약서 텍스트) |
| `LANGGRAPH_URL`   | AI 분석 / Q&A 가 `lib/agent/mock.ts` 응답으로 폴백 |

### 3. 데모 시나리오 (60초)

1. `http://localhost:3000` 접속 → "지금 검토 받기"
2. `docs/근로기준법.pdf` 또는 본인 계약서 업로드
3. 분석 페이지에서 위반 카드(최저임금/근로시간/휴게/주휴) 확인
4. 하단 챗 박스에서 "주휴수당이 뭔가요?" 등 질문 → 근로기준법 RAG 답변

---

## 📂 디렉토리 구조

```
team3-ailaborattorney/
├── README.md                         ← 이 문서
│
├── frontend/                         ← Next.js 15 App Router
│   ├── app/
│   │   ├── api/
│   │   │   ├── upload/route.ts       # 파일 업로드 + SQLite 행 생성
│   │   │   ├── analyze/route.ts      # OCR → Parser → Rules → AI Agent
│   │   │   └── qa/route.ts           # 분석 컨텍스트 기반 Q&A + 로그 저장
│   │   ├── analysis/[id]/            # 분석 결과 (요약 카드 + 위반 카드 그리드)
│   │   ├── upload/page.tsx           # 업로드 페이지
│   │   ├── globals.css               # Tailwind 4 @theme 토큰 (toss-blue, semantic)
│   │   ├── layout.tsx                # sticky 헤더 + Pretendard
│   │   └── page.tsx                  # 랜딩 (3-step + CTA)
│   ├── components/
│   │   ├── ui/                       # Button · Card · Badge · Icon
│   │   ├── upload-form.tsx           # 드래그&드롭 + 진행 인디케이터
│   │   ├── violation-card.tsx        # RiskBadge + "이렇게 해보세요" 카드
│   │   ├── risk-badge.tsx            # 안전 / 주의 / 위반 가능 배지
│   │   └── qa-chat.tsx               # 토스 메신저 풍 Q&A 채팅
│   ├── lib/
│   │   ├── db.ts                     # better-sqlite3 싱글톤
│   │   ├── ocr/                      # Upstage Document Parse + mock
│   │   ├── parser/                   # OCR → ContractData
│   │   ├── rules/                    # 4종 룰 (min_wage / working_hours / break_time / weekly_rest)
│   │   └── agent/                    # LangGraph fetch 클라이언트 + mock + types
│   ├── db/schema.sql                 # contracts / qa_logs 테이블 정의
│   ├── public/                       # 정적 자산
│   ├── uploads/                      # 업로드된 계약서 (gitignored)
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── next.config.ts · tsconfig.json · postcss.config.mjs
│   └── .env.example
│
├── backend/                          ← FastAPI + LangGraph
│   ├── server.py                     # /qa, /analyze 엔드포인트 (qa_graph / analyze_graph 래핑)
│   ├── requirements.txt
│   ├── chroma_db.zip                 # 근로기준법 임베딩 ChromaDB (unzip 시 chroma_db/)
│   └── .env.example                  # UPSTAGE_API_KEY · UPSTAGE_MODEL · CHROMA_DIR
│
└── docs/                             ← 참고 자료
    ├── labor_law_rag.ipynb           # qa_graph / analyze_graph 레퍼런스 노트북
    └── 근로기준법.pdf                  # 임베딩 원본 (문서 파싱 / 청킹 대상)
```

---

## 🔌 API 엔드포인트

### Frontend (Next.js Route Handlers)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/api/upload`        | `multipart/form-data` (file, weekly_hours?, age?) → `{ id }` |
| `POST` | `/api/analyze`       | `{ id }` → `{ id, parsed, rule, ai }` |
| `GET`  | `/api/analyze?id=`   | 분석 결과 조회 |
| `POST` | `/api/qa`            | `{ contractId, question }` → `{ answer, references?, source? }` |
| `GET`  | `/api/qa?contractId=` | 과거 Q&A 로그 |

스키마는 `frontend/lib/agent/types.ts` 단일 출처.

### Backend (FastAPI)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET`  | `/`         | health · version · 사용 모델 |
| `POST` | `/qa`       | `{ question, context? }` → `{ answer, references }` |
| `POST` | `/analyze`  | `{ contract_data, rule_violations }` → `{ violations[], summary }` |

---

## 🤖 LangGraph 그래프

`backend/server.py` 는 노트북(`docs/labor_law_rag.ipynb`) 의 두 그래프를 그대로 FastAPI 로 래핑합니다.

- **qa_graph**: `retrieve` → `generate` (근로기준법 ChromaDB 에서 top-k 검색 후 Solar 답변 생성)
- **analyze_graph**: 룰 엔진이 찾은 위반 항목을 입력받아 위험도·권장 조치·근거 조항을 생성

벡터 DB 는 `근로기준법.pdf` 를 청크 단위로 임베딩한 ChromaDB 로, 사전 빌드 결과를 `chroma_db.zip` 으로 동봉합니다 (재빌드 불필요).

---

## ⚠️ 면책

본 서비스는 자동 검토 결과를 제공하며 **법적 자문이 아닙니다**. 정확한 판단은 노무사 또는 노동청(국번 없이 1350) 상담을 권장합니다.

---

## 📝 라이선스 / 출처

- 근로기준법 원문: 국가법령정보센터 (공공누리)
- 디자인 영감: 토스(Toss) Design System
- 본 코드: SW 마에스트로 17기 Team 3 — 내부 학습/제출용
