# 맞춤형 운동 스케줄링 에이전트

캘린더·건강·운동기록을 종합해 이번 주 맞춤 운동 스케줄을 자동 생성·재조정하는 LangGraph Agent + Flutter Web 프로젝트.

> 발표일: **2026-05-15(금)** · 코드 동결: **2026-05-10(일)** · `v1.0-demo`

## 무엇을 하나

- 사용자의 **이번 주 캘린더 일정 / 건강 컨디션 / 최근 운동 이력**을 한 화면에 통합한다.
- 우측 채팅에서 *"이번 주 운동 일정 짜줘"* 라고 하면 LangGraph 에이전트가 일주일치 운동 슬롯(부위·강도·시간)을 제안한다.
- *"화요일은 피곤할 것 같아"* 같은 자연어 재조정에 대해 멀티턴으로 해당 일자만 변경한다.
- 제안된 슬롯을 한 번에 캘린더에 등록할 수 있고, 등록된 슬롯은 부위별 피로도 레이더 차트에 즉시 반영된다.

## 화면

데모 메인은 좌측 카드 3종(이번 주 일정 / 컨디션 / 최근 운동) + 가운데 부위별 피로도 레이더 + 우측 AI 코치 채팅 한 페이지.

## 아키텍처

```
Flutter Web (frontend/)
  ├── Supabase SDK 직접 CRUD ─────────────► Supabase (Postgres)
  │     calendar_events / health_snapshots / workout_records
  └── SSE chat client ─────► FastAPI gateway (backend/)
                                  └─► LangGraph Agent (agent/)
                                          ├─► OpenAI GPT-4o
                                          ├─► tools/data_tools.py ─► Supabase
                                          └─► memory/ (LangGraph checkpointer)
```

- **Frontend**: Flutter Web (Dart). 카드 UI + Supabase 직접 CRUD + SSE 채팅 클라이언트.
- **Backend**: FastAPI 게이트웨이. `/agent/chat` SSE 엔드포인트 한 곳으로 좁힌 인터페이스(검증·직렬화·에러 매핑만 담당, 비즈 로직은 `agent/`).
- **Agent**: LangGraph 그래프. 외부 LLM 호출은 `agent/nodes.py` 한 곳에 모아 다른 모듈에서 직접 호출 금지.
- **Tools**: `tools/data_tools.py`가 calendar / health / workouts CRUD 12개를 한 모듈에 모아 노출. 모든 데이터 접근의 단일 창구.
- **Schemas**: Pydantic 모델이 Supabase 테이블 스키마와 1:1 매핑. 변경은 `[interface-change]` PR 5명 react 룰.

## 기술 스택

- **Backend**: Python 3.11+ · FastAPI · uvicorn · sse-starlette · LangGraph · LangChain · OpenAI GPT-4o · Pydantic v2 · supabase-py
- **Frontend**: Flutter Web · supabase_flutter · fl_chart · lucide_icons · shared_preferences
- **Datastore**: Supabase (Postgres). 의존성은 [`requirements.txt`](requirements.txt) / [`frontend/pubspec.yaml`](frontend/pubspec.yaml)
- **Memory**: LangGraph in-memory checkpointer (필요 시 SQLite로 교체 가능한 구조)

## 빠른 시작

### 1. 사전 준비

- Python 3.11+, Flutter SDK 3.6+, Supabase 프로젝트(URL + anon key + service role key)
- `.env`를 [`/.env.example`](.env.example) 복사해 채운다 — `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

### 2. Supabase 스키마

`calendar_events`, `health_snapshots`, `workout_records` 세 테이블이 필요하다. 모델은 [`schemas/models.py`](schemas/models.py)와 1:1 매핑. RLS 정책은 데모 범위에 맞춰 anon 읽기/쓰기 허용으로 설정.

### 3. Backend (FastAPI + Agent)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload         # http://localhost:8000/docs
```

### 4. Frontend (Flutter Web)

```bash
cd frontend
flutter pub get
flutter run -d chrome \
  --dart-define=SUPABASE_URL=https://<project>.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=<anon-key>
```

### 5. KPI 시나리오 시딩

```bash
# 프로젝트 루트
python data/seed_scenario.py 4   # KPI 4: 멀티턴 재조정
```

`data/seed_scenario.py <1~5>`로 시나리오별 데이터를 Supabase에 적재한다. 날짜는 실행 시점의 현재 주 월요일 기준으로 자동 조정되므로 언제 실행해도 된다.

## KPI 시나리오 (5/9 통과 기준)

| # | 파일 | 통과 조건 | 채팅 검증 방법 |
|---|---|---|---|
| 1 | `data/scenarios/01_full_week.json` | 빈 시간 0인 주에 10분 대체 루틴 제안 | "이번 주 운동 추천해줘" → 모든 슬롯 10분 이하 |
| 2 | `02_sleep_deprived.json` | 수면 부족 시 강도 하향 | "이번 주 운동 추천해줘" → 강도 ≤2 |
| 3 | `03_consecutive_muscle.json` | 일정 충돌률 1% 미만 + 연속 부위 회피 | 충돌 0건 + 하체 미포함 |
| 4 | `04_multiturn.json` | 멀티턴 재조정이 해당 일자만 변경 | 1턴 추천 → "화요일은 피곤할 것 같아" → 화요일만 변경 |
| 5 | `05_free.json` | 추천 부위와 레이더 차트 색상 변화 일치 | 가슴·삼두 미포함 + 레이더 갱신 |

## 레포 구조

```
exercise-planning/
├── frontend/        Flutter Web 클라이언트
├── backend/         FastAPI 게이트웨이 (api/{data,chat}.py)
├── agent/           LangGraph 그래프 + 노드 + 프롬프트
├── memory/          LangGraph 체크포인터
├── tools/           data_tools.py — Supabase CRUD 단일 창구
├── data/            가상 JSON + scenarios/ + seed_scenario.py
├── schemas/         Pydantic 모델 (Supabase와 1:1)
├── tests/           스모크 / 단위 / KPI
├── docs/            기획·분담·디자인
└── scripts/         demo_run.py · scenario_test.py
```

각 디렉토리에 자체 `CLAUDE.md`가 있어 슬라이스 단위 책임·인터페이스 락 지점이 정리되어 있다.

## 팀 / 슬라이스 분담

| 슬라이스 | 담당 | 영역 |
|---|---|---|
| **A** Flutter Web 프론트 | 노준영 | `frontend/` 셸·카드·레이더·Supabase 래퍼 |
| **B** Chat UI + 통신 프로토콜 | 박장우 | `frontend/lib/chat/` + SSE 청크 스펙 |
| **C** LangGraph Agent | 이유준 | `agent/`, `memory/`, 프롬프트 |
| **D** CRUD Tool + Tech Lead | 박영준 | `tools/data_tools.py`(calendar+workouts), 시딩, 통합 |
| **E** CRUD Tool + 시나리오 | 신승민 | `tools/data_tools.py`(health), `data/scenarios/`, 프롬프트 튜닝 |

## 협업 규칙

- `main` 보호. 브랜치는 `feat/<A~E>-<짧은설명>`. PR은 함수/엔드포인트 단위로 작게.
- **인터페이스 변경**(`schemas/models.py` · Tool 시그니처 · REST · SSE 청크)은 PR 제목에 `[interface-change]` 태그를 붙이고 5명 모두 react 후 머지.
- 셀프 머지 금지. 같은 파일을 여럿이 만질 때는 PR 코멘트로 머지 순서 합의.
- `.env` 절대 커밋 금지. 새 변수는 `.env.example`에 키만 추가.
- UI/챗 응답은 한국어, 코드·주석·식별자는 영어. 외부 LLM 호출은 `agent/nodes.py` 한 곳에 모음.
