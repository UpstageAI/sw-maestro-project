# 커널을 좋아하는 옆자리의 그녀

> Software Maestro 1조 — LLM 기반 대화형 비주얼 노벨

LLM 기반 대화와 상태 시스템을 결합한 웹 비주얼 노벨 인터랙티브 게임입니다. 정해진 선택지 대신 **자유 입력 대화**로 캐릭터와 관계를 쌓고, 누적된 호감도와 흐름에 따라 엔딩이 결정됩니다.

---

## 프로젝트 소개

### 무엇인가

Software Maestro 환경을 배경으로, 플레이어는 팀 동료인 캐릭터 **이세라**와 자유롭게 대화하며 관계를 형성합니다. 단순히 선택지를 고르는 것이 아니라 직접 텍스트를 입력해 대화하고, 그 내용에 따라 호감도와 스토리가 실시간으로 변화하는 것을 경험합니다.

### 왜 만들었는가

기존 비주얼 노벨은 제한된 선택지와 고정된 스토리 구조로 인해 플레이어의 자유로운 표현과 몰입감 있는 상호작용을 제공하기 어렵습니다. 본 프로젝트는 LLM을 활용해 사용자의 자유로운 입력을 기반으로 캐릭터가 반응하도록 함으로써, 기존 비주얼 노벨의 구조적 한계를 극복하고 **"내 말로 관계를 만들어가는 경험"** 을 제공하는 것을 목표로 합니다.

### 핵심 특징

- **LLM 자유 입력 대화** — 선택지 없이 자연어로 캐릭터와 실시간 스트리밍 대화
- **상태 기반 진행 시스템** — 호감도 / 씬 / 이벤트가 백엔드 룰 엔진에 의해 결정
- **6종 분기 엔딩** — 호감도 임계값에 따라 Bad / Normal / Happy / Marriage 등으로 분기
- **감정 기반 표정 변화** — 발화마다 감정 분석 결과로 캐릭터 스프라이트가 변경
- **자동 저장 & 이어하기** — 세션 상태를 백엔드와 동기화

### 참여자

김민성, 김영주, 김재원, 양하정, 이병윤

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| 프론트엔드 | [Monogatari](https://monogatari.io/) (비주얼 노벨 엔진), Vanilla JS (ES Modules), HTML5 / CSS3 |
| 백엔드 | FastAPI, LangGraph (3-노드 파이프라인), SSE 스트리밍 |
| 데이터베이스 | PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) |
| LLM | [Upstage Solar](https://console.upstage.ai) `solar-pro3` (OpenAI 호환 클라이언트) |
| 인프라 | Docker / Docker Compose, uv (Python 의존성), Alembic |

---

## 시스템 아키텍처

```
사용자
  ↓
Frontend (Monogatari SPA, :5500)
  ↓ REST + SSE
Backend (FastAPI, :8000)
  ├── Session / State 관리 + Trigger 룰 엔진
  └── LangGraph: retrieve_context → guardrail → evaluate_affinity
        ↓
       Upstage Solar LLM
  ↓
PostgreSQL + pgvector (세션 · 대화 · 임베딩)
```

호감도·씬 전환·엔딩 결정 등 게임 룰은 모두 백엔드에서 결정하며, LLM은 응답 생성과 감정/호감도 델타 산출만 담당합니다.

---

## 실행 방법

### 사전 요구 사항

- Docker / Docker Compose
- Node.js 14+ (프론트 정적 서버용)
- Upstage Solar API 키

### 1) 백엔드 (Docker Compose 권장)

```bash
cd backend
cp .env.example .env          # SOLAR_API_KEY 채우기
docker compose up --build
```

부팅 후 헬스 체크:

```bash
curl http://localhost:8000/api/v1/health
```

로컬 uv 개발, Alembic 마이그레이션, SSE 수동 검증 시나리오는 [backend/README.md](backend/README.md)를 참고하세요.

### 2) 프론트엔드

```bash
cd frontend
npm install -g http-server
http-server . -p 5500 -o
```

또는 VS Code의 **Live Server** 확장으로 `index.html`을 엽니다. `http://localhost:5500`에서 게임이 시작됩니다.

> `index.html`을 파일 탐색기에서 직접 더블클릭하면 ES 모듈 제한으로 동작하지 않습니다. 반드시 HTTP 서버를 통해 열어야 합니다.

상세한 파일 구조와 백엔드 API 매핑은 [frontend/README.md](frontend/README.md)를 참고하세요.

---

## 디렉토리 구조

```
team1-myseatmateisintokernels/
├── frontend/   # Monogatari 기반 비주얼 노벨 클라이언트
└── backend/    # FastAPI + LangGraph + pgvector
```

---

## 참고 문서

- [프로젝트 기획서 (Google Docs)](https://docs.google.com/document/d/1WBNWzPA4tzB-x0tMO7lSSI2ff3IrLIFz4CmYc2HXPUk/edit?usp=sharing)
- [frontend/README.md](frontend/README.md)
- [backend/README.md](backend/README.md)
