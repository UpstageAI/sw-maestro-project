# 43조 — 맞춤형 운동 스케줄링 에이전트

> 5인 팀 공유 컨텍스트. 이 파일 수정은 PR로만 (인터페이스/구조 변경은 5명 모두 react 후 머지).
> **각 디렉토리에 자체 `CLAUDE.md`가 있음** — 슬라이스별 디테일은 거기에서 본다.

**한 줄 정의**: 캘린더·건강·운동기록을 종합해 이번 주 맞춤 운동 스케줄을 자동 생성·재조정하는 LangGraph Agent + Flutter Web UI. 상세 기획·분담·일정은 [`docs/`](docs/CLAUDE.md) 참조 (분담 원본은 `docs/planning/plan.md`).

## 0. Claude에게 — 작업 시작 전 본인 확인 (필수)

이 레포는 5명이 슬라이스를 나눠 작업한다(A~E). 같은 레포라도 사람마다 컨텍스트가 완전히 다르니, **새 세션 시작 시 먼저 본인이 누군지 확인**:

1. **묻기** — 사용자에게:
   > "어느 슬라이스로 작업하시나요? **A** 노준영 (Flutter 프론트) / **B** 박장우 (Chat UI + 프로토콜) / **C** 이유준 (LangGraph Agent) / **D** 박영준 (CRUD calendar+workouts + Tech Lead) / **E** 신승민 (CRUD health + 시나리오·튜닝 주도)"
2. **읽기** — 답에 따라 두 파일을 우선 정독:
   - `docs/planning/people/<X>_<이름>.md` ← 본인 일자별 to-do, 합의 책임, 흔한 함정
   - 본인 주 디렉토리의 `CLAUDE.md` (예: A → `frontend/CLAUDE.md`, C → `agent/CLAUDE.md`, D/E → `tools/CLAUDE.md`)
3. **작업** — 본인 슬라이스 컨텍스트 위주로 진행. 다른 슬라이스 디렉토리(예: B가 `tools/` 변경)를 만져야 하면 사용자에게 명시적으로 확인.
4. **인터페이스 변경 시** — `[interface-change]` PR 태그 + 5명 react 룰 (5번 협업 규칙) 안내.
5. **메모리** — 사용자가 본인 슬라이스를 알려주면 메모리에 저장 (다음 세션부터는 묻지 말 것). 단, 같은 사용자가 슬라이스를 바꿀 가능성이 있으니 새 작업 흐름이 다른 슬라이스 같으면 한 번 더 확인.

> **예외**: 사용자가 처음부터 "B 슬라이스 작업할게" 같이 명시하면 1번 묻기 생략하고 2번부터.

## 1. 팀 & 담당 슬라이스 (역할 분담 — 확정)

| # | 슬라이스 | 담당 | 디렉토리·책임 |
|---|---|---|---|
| **A** | Flutter Web 프론트 (대시보드) | **노준영** | `frontend/` 전체. 좌측 카드 3종(일정/컨디션/최근 운동) + 가운데 부위별 피로도 레이더. **Supabase SDK 직접 CRUD** (FastAPI `/data/*` 우회). |
| **B** | Chat UI + Agent 통신 프로토콜 | **박장우** | `frontend/lib/chat/` (FE 채팅, SSE 클라이언트, 디자인) + `backend/api/chat.py` 스펙 (C와 공동). Stream 구현. |
| **C** | LangGraph Agent (prompt + graph + memory) | **이유준** | `agent/`, `memory/`. `run_agent_stream` 진입점, SSE 청크 emit. |
| **D** | CRUD Tool (calendar + workouts) + Tech Lead | **박영준** | `tools/data_tools.py` (calendar·workouts CRUD 8개) + `data/calendar.json`·`workouts.json` 시딩 + Supabase 연결 |
| **E** | CRUD Tool (health) + 시나리오 + 프롬프트 튜닝 | **신승민** | `tools/data_tools.py` (health CRUD 4개) + `data/health.json` + `data/scenarios/` 5개 적재 주도 + `agent/prompts.py` 튜닝 (C와) |

**Tech Lead**: **D 박영준** — 매일 저녁 main 동작 확인 + Flutter↔FastAPI 통합 책임. CRUD가 패턴 반복이라 후반 여유가 있고, FE/Agent 사이 데이터 흐름의 진실을 가장 잘 봄.

**원칙**(`docs/planning/plan.md` 직역): "유저가 FE에서 보는 모든 데이터는 agent도 그대로 본다." → A의 화면에 뜨는 모든 항목에는 D/E가 read+write Tool을 노출.

## 2. 기술 스택

- **Backend**: Python 3.11+ / FastAPI / uvicorn / sse-starlette / LangGraph(+LangChain) / OpenAI GPT-4o / Pydantic v2 / supabase-py
- **Frontend**: Flutter Web (Dart) / supabase_flutter
- **Datastore**: Supabase (PostgreSQL). 실제 Google Calendar/Apple Health API 미연동. `schemas/models.py`가 Supabase 테이블 스키마와 1:1 매핑.
- **Agent 메모리**: LangGraph 체크포인터 (in-memory → 필요 시 SQLite)
- **의존성**: Python은 `requirements.txt`, Flutter는 `frontend/pubspec.yaml`. 추가 시 팀 채널 공지 + PR 설명에 명시.

## 3. 레포 구조

```
AI_TECH_EDU/
├── frontend/    # A 노준영 (Flutter Web), B 박장우 (lib/chat/) → frontend/CLAUDE.md
├── backend/     # FastAPI 게이트웨이 (B/C/D/E 합의 지점) → backend/CLAUDE.md
│   ├── main.py
│   └── api/{data,chat}.py
├── agent/       # C 이유준 (LangGraph)        → agent/CLAUDE.md
├── memory/      # C 이유준 (체크포인터)       → memory/CLAUDE.md
├── tools/       # D 박영준 + E 신승민 (CRUD)  → tools/CLAUDE.md
├── data/        # D + E (가상 JSON + 시나리오) → data/CLAUDE.md
│   └── scenarios/
├── schemas/     # 전원 공유 (Pydantic 모델)   → schemas/CLAUDE.md
├── tests/       # 스모크/단위/KPI            → tests/CLAUDE.md
├── docs/        # 분담·일정·스펙·디자인       → docs/CLAUDE.md
│   ├── planning/  (plan.md, dev_plan.md, 킥오프_5월4일.md)
│   ├── spec/      (feature_spec.md, 프로젝트 기획서 양식_*.md)
│   └── design/    (flow.html, 메인 화면 PNG)
└── requirements.txt  .env.example
```

작업 시작 전 자기 슬라이스 디렉토리의 `CLAUDE.md`를 먼저 읽기.

## 4. 인터페이스 진입점 (자세한 모델은 `schemas/CLAUDE.md`)

```python
# tools/data_tools.py — D, E (Agent 전용 Supabase 접근)
get_calendar(start, end) -> list[CalendarEvent]
create_calendar_event(event) -> CalendarEvent
update_calendar_event(id, patch) -> CalendarEvent
delete_calendar_event(id) -> None
# health, workouts 동일 패턴 (내부 구현은 supabase-py, 시그니처는 락)

# agent/graph.py — C
async def run_agent_stream(user_input, thread_id) -> AsyncIterator[ChatChunk]
# (비스트림 run_agent도 보존 — 테스트·단순 호출용)

# backend/api/ — FastAPI 라우터 (/data/* 없음 — Flutter가 Supabase 직접 호출)
POST   /agent/chat   (SSE)             -> stream of ChatChunk
GET    /health                          -> ping
```

위 시그니처는 **이미 락**. 변경 절차는 `schemas/CLAUDE.md` 참고.

## 5. 협업 규칙

- **Git**: `main` 보호, 브랜치 `feat/<A~E>-<짧은설명>`, PR은 함수/엔드포인트 단위로 작게, 리뷰어 1명 이상 승인 후 머지(셀프 머지 금지). 같은 파일(`tools/data_tools.py`)을 여럿이 만질 땐 PR 코멘트로 머지 순서 합의.
- **Mock-first**: 데이터/타 슬라이스 함수가 없어도 `schemas/` 더미와 `NotImplementedError` / `501` stub으로 작업 시작. 실제 LLM 호출은 5/8 통합 전까지 stub 가능.
- **합의 메커니즘 (회의 없음)**: 일상 작업은 본인 판단으로 진행. **인터페이스 변경**(`schemas/models.py`·Tool 시그·REST·SSE 청크)이 필요하면 PR 제목에 `[interface-change]` 태그 + 5명 모두 react 후 머지. 막힌 게 있으면 GitHub Issue 또는 팀 채널.
- **시크릿**: `.env` 절대 커밋 금지(`.gitignore` 등록), 새 변수는 `.env.example`에 키만 추가.

## 6. 코딩 컨벤션

타입 힌트 필수. UI/챗 응답은 한국어, 코드·주석·식별자는 영어. 주석은 *왜*가 비자명할 때만. LangGraph 노드는 한 가지 일만. **외부 LLM 호출은 `agent/nodes.py` 한 곳에 모음**(다른 모듈 직접 호출 금지). FastAPI 라우터는 비즈니스 로직 금지(검증·직렬화·에러 매핑만, 실제 일은 `tools/`/`agent/`).

## 7. 환경 셋업

```bash
# Backend (Python)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # OPENAI_API_KEY + SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY 채우기
uvicorn backend.main:app --reload      # http://localhost:8000/docs (Swagger)
pytest

# Supabase (A/노준영이 5/5에 프로젝트 생성 → 팀 채널 공유)
# 1. supabase.com 에서 새 프로젝트 생성
# 2. SQL Editor에서 테이블 생성 (calendar_events / health_snapshots / workout_records)
# 3. SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY 를 팀 채널에 공유
# 4. 전원 .env 파일에 추가

# Frontend (Flutter Web — A가 5/5에 셋업)
cd frontend
flutter create .
# pubspec.yaml에 supabase_flutter: ^2.0.0 추가 후:
flutter pub get
flutter run -d chrome
```

## 8. 일정 (2026-05-04 ~ 05-10, 코드 동결)

| 날짜          | 마일스톤                                       |
| ----------- | ------------------------------------------ |
| 5/4 (월)     | 인터페이스 락(REST + SSE 청크 + Tool 시그니처), 레포 재편, LangGraph 튜토리얼 1시간 페어 학습 |
| 5/5 (화)     | A `flutter create` + 카드 1종, B 채팅 셸, C agent stub 그래프 1회 실행, D/E CRUD 첫 함수 |
| 5/6 (수)     | 핵심 로직 (1주치 데이터, Tool 연결, 스케줄 도출)           |
| 5/7 (목)     | 멀티턴 메모리, 재조정 흐름                            |
| **5/8 (금)** | **★ 1차 통합 — Flutter ↔ FastAPI ↔ Agent end-to-end 1회 성공** |
| 5/9 (토)     | 통합 테스트, KPI 시나리오 5개, 엣지 케이스                |
| 5/10 (일)    | **코드 동결**, 데모 시나리오 무사고 시연, 태그 `v1.0-demo`  |

발표일: **2026-05-15(금)**. 5/11~14는 발표 자료·리허설.

## 9. KPI 시나리오 (5/9 통과 목표)

1. 일정 충돌률 1% 미만 (10회 생성 시 충돌 0회)
2. 피로도 "높음" 부위에 해당 부위 운동 추천 0회
3. 빈 시간 없는 주에 10분 대체 루틴(홈트·계단) 제안
4. 멀티턴 재조정 ("화요일은 피곤할 것 같아") → 해당 일자만 변경
5. 추천 부위와 FE 레이더 차트 색상 변화 일치

각 시나리오 입력은 `data/scenarios/*.json`에서 관리 (D/E).

## 10. 절대 하지 말 것

- 실제 Google Calendar / Apple Health API 연동 (MVP 범위 외)
- `.env`·API 키 커밋, `main` 직접 push, 셀프 머지
- `schemas/models.py`·Tool 시그니처·API 엔드포인트를 단독 결정으로 변경
- 다른 슬라이스 디렉토리를 합의 없이 리팩터링
- 사용자에게 보여줄 메시지를 영어로 작성
- FastAPI 라우터에서 OpenAI 직접 호출 (전부 `agent/nodes.py` 경유)
- JSON 파일 직접 편집으로 데이터 변경 (Supabase가 단일 진실 소스)
