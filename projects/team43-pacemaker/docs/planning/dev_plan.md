# 43조 개발 계획 (재작성판 — plan.md 합의 반영)

> **이 문서가 답하는 것**: 누가, 언제, 무엇을, 어떻게 만드는가.
> **이 문서가 답하지 않는 것**: 왜 이 기능이 필요한가 → `../spec/프로젝트 기획서 양식_*.md`. 사용자가 보는 화면이 뭔가 → `../spec/feature_spec.md`. 함수 시그니처 → `../../schemas/CLAUDE.md`. 분담 원본 → `plan.md` (같은 디렉토리).

- **개발 기간**: 2026-05-04(월) ~ 2026-05-10(일), 7일
- **코드 동결**: 5/10(일) EOD
- **발표일**: 2026-05-15(금)
- **MVP**: LangGraph Agent + FastAPI 게이트웨이 + Flutter Web UI

---

## 1. 5명 분배 (A~E 역할 분담, 확정)

원칙: 백엔드/프론트엔드 비대칭 없이, 기능 영역별로 풀스택 책임을 분리. "유저가 FE에서 보는 모든 데이터는 agent도 그대로 본다."

| 슬라이스 | 한 줄 책임 | 담당 기능 (feature_spec) | 담당자 |
|---|---|---|---|
| **A** | Flutter Web 프론트 (대시보드 — 좌측 카드 3종 + 가운데 레이더) | F1, F2, F3, F5 | **노준영** |
| **B** | Chat UI + Agent 통신 프로토콜 (SSE stream) | F4·F6의 FE 측, F7 | **박장우** |
| **C** | LangGraph Agent (prompt + graph + memory) | F4·F6의 BE 측 | **이유준** |
| **D** | CRUD Tool (calendar + workouts) + Tech Lead | F1·F3·F7의 데이터 측 + 통합 책임 | **박영준** |
| **E** | CRUD Tool (health) + scenarios 5개 적재 + 프롬프트 튜닝 주도 | F2의 데이터 측 + KPI 시나리오 운영 | **신승민** |

**Tech Lead = D 박영준** (확정). 매일 저녁 main 동작 확인 + Flutter↔FastAPI 통합 책임. CRUD가 패턴 반복이라 후반 여유 있고, FE/Agent 사이 데이터 흐름의 진실을 가장 잘 봄.

**작업량 균형**:
- D는 CRUD 양 많음(8개) + Tech Lead — 패턴 반복이라 빠르고, 통합 점검은 짧은 시간
- E는 CRUD 적음(4개) + 시나리오 5개 + 프롬프트 튜닝 — 데이터/문서 작업 비중 큼
- C는 LangGraph 핵심만 — 시나리오 케이스/튜닝은 E가 주도, KPI 자동화 시나리오 매칭은 D/E가 짜고 C는 그래프 검증만

### 인접 협업 (이미 락 완료)

- **A ↔ B**: 같은 Flutter 앱. A는 `lib/cards/`, `lib/api/`. B는 `lib/chat/`. PR 디렉토리로 분리.
- **A ↔ D/E**: Supabase 테이블 스키마 (`calendar_events` / `health_snapshots` / `workout_records`) — `schemas/models.py` 모델 그대로. **이미 락**.
- **B ↔ C**: SSE 청크 포맷(`ChatChunk.type`별 payload) — `schemas/CLAUDE.md` 표 참조. **이미 락**.
- **C ↔ D/E**: Tool 시그니처(`get_/create_/update_/delete_*`) — `tools/CLAUDE.md`. **이미 락**. C는 LangGraph `@tool`로 래핑해 호출.

### 장점과 리스크

- **장점**: FE/BE 분리가 자연스러워 병렬성 최대. 회의 없이도 인터페이스가 박혀 있어 충돌 적음.
- **리스크**: Flutter Web이 처음인 팀원(A·B)은 셋업에 시간 소요. C의 LangGraph 학습 부담이 가장 큼 — 5/4 시작 직후 Quickstart 1회 비동기 학습 권장.

---

## 2. 통합 전략 (3가지 핵심 약속)

### 약속 1. 인터페이스는 이미 락됨

`schemas/models.py`(Pydantic) + `backend/api/`(FastAPI 라우터) + `tools/data_tools.py`(시그니처)에 박혀 있음. 변경은 `[interface-change]` PR + 5명 react로만.

대상 모델: `CalendarEvent`, `HealthSnapshot`, `WorkoutRecord`, `WorkoutSlot`, `MuscleFatigueState`, `ScheduleProposal`, `ChatRequest`, `ChatChunk`, `AgentResponse`.

대상 함수/엔드포인트:
```python
# Tool (D/E) — 내부 구현은 supabase-py, 시그니처는 락
get_/create_/update_/delete_calendar_event
get_/create_/update_/delete_health_snapshot
get_/create_/update_/delete_workout

# Agent (C)
async run_agent_stream(user_input, thread_id) -> AsyncIterator[ChatChunk]

# FastAPI (B/C 합의) — /data/* 없음, Flutter가 Supabase 직접 호출
POST /agent/chat (SSE)
GET  /health
```

### 약속 2. 더미 데이터로 먼저 동작시킨다

다른 사람의 실제 함수를 기다리지 말고 더미로 자기 슬라이스를 일단 돌려본다. 5/8 통합 전까지 LLM 호출도 stub OK.

- D/E (Tool): Supabase 테이블 연결 후 `get_*` 부터 채움
- C (Agent): stub Tool로 그래프 골격, `run_agent_stream`이 더미 청크 yield (이미 구현됨)
- A/B (FE): BE가 501 돌려줘도 UI 로딩/에러 상태로 화면을 먼저 그림

### 약속 3. 같은 파일 동시 수정은 함수/엔드포인트 단위 PR로 쪼갠다

`tools/data_tools.py`(D, E)를 둘이 만진다. PR 제목에 `[tools] create_calendar_event 구현` 식으로 자기 함수를 명시하고, 같은 파일 PR이 겹치면 PR 코멘트로 머지 순서 합의 (먼저 올린 사람이 머지 우선).

---

## 3. 일자별 카드

각 카드에 그날 끝나야 하는 것, 5명이 그날 무엇을 하는가, 합격 기준 체크리스트를 적었다.

> **본인 to-do만 빠르게 보려면** `people/<본인>.md` (예: `people/A_노준영.md`) — 같은 일정을 사람 시점으로 정리.

### 5/4 (월) — 비동기 시작 (회의 없음)

**그날의 목표**: EOD까지 모든 사람의 stub PR이 main에 들어가 있다.

전원 공통 (비동기):
- 환경 셋업 (`킥오프_5월4일.md` 시작 체크리스트 참조)
- LangGraph 공식 Quickstart 1회 (각자 본인 페이스로) — C는 더 깊게
- 본인 슬라이스 디렉토리 `CLAUDE.md` + `docs/planning/people/<본인>.md` 정독

각자:
- **A**: `frontend/`에 `flutter create .` 실행, 빈 화면 1회 띄움 (`flutter run -d chrome`)
- **B**: `frontend/lib/chat/` 디렉토리 + 채팅 위젯 골격 PR (입력창 + 메시지 리스트만)
- **C**: 시스템 프롬프트 초안 (`agent/prompts.py`에 ReAct 3단계 강제 문구) — `run_agent_stream` 더미 청크는 이미 구현됨
- **D**: `data/calendar.json` 더미 5건 + `get_calendar` 1차 구현 (JSON 파싱)
- **E**: `data/health.json` 더미 5건 + `get_health` 1차 구현 (JSON 파싱)

**합격 기준**:
- [ ] 5명 각자 첫 PR이 main에 머지됨
- [ ] `uvicorn backend.main:app --reload`로 부팅, `GET /health` 200 OK
- [ ] `pytest`가 통과
- [ ] (A) `flutter run -d chrome`으로 빈 Flutter Web 화면 떠 있음

---

### 5/5 (화) — 더미 입력으로 단독 실행

**그날의 목표**: 5명 각자가 자기 슬라이스를 단독으로 돌릴 수 있다.

각자:
- **A**: Supabase 프로젝트 생성 + `supabase_flutter` 초기화 + 좌측 카드 1종 더미 렌더 + `lib/api/` Supabase 쿼리 1개
- **B**: 채팅창 입력→stub 응답 루프, SSE 스트림 수신 골격 (백엔드 stub과 연결)
- **C**: stub Tool로 그래프 1회 실행 성공, `tool_call` 청크 emit 시작
- **D**: Supabase `calendar_events`·`workout_records` 연결 후 `get_*` 완성, CRUD 중 첫 write 함수 1개
- **E**: D와 동일 (`health_snapshots` 도메인)

**합격 기준**:
- [ ] 각 슬라이스가 단위 테스트 1개씩 통과 (`tests/test_<A~E>_*.py`)
- [ ] FastAPI Swagger(`/docs`)에서 POST /agent/chat stub 200 응답
- [ ] Flutter 화면이 Supabase에서 받은 데이터를 카드에 표시

---

### 5/6 (수) — 핵심 로직

**그날의 목표**: 1주치 데이터로 추천이 도출된다 (LLM은 아직 stub 가능).

각자:
- **A**: 좌측 카드 3종 + 가운데 피로도 레이더 모두 실데이터 연동
- **B**: SSE `text` 청크 누적 표시, `proposal` 청크 받으면 추천 슬롯 카드로 렌더
- **C**: 페르소나 톤 프롬프트 완성, 빈 시간 탐색 + 운동 매칭 로직 (스케줄 도출)
- **D/E**: `create_/update_/delete_*` 일부 구현, 1주치 더미 데이터 보강

**합격 기준**:
- [ ] stub LLM이라도 `ScheduleProposal` SSE `proposal` 청크가 FE에 도달
- [ ] 피로도 누적이 운동 기록을 반영함 (FE 레이더에 차이 보임)

---

### 5/7 (목) — 멀티턴 + 엣지 케이스 데이터

**그날의 목표**: 재조정 흐름이 동작하고, KPI 5개에 필요한 데이터가 준비된다.

각자:
- **A**: 카드 로딩/에러 상태, 색상 단계화 (피로도 0=초록 → 5=빨강)
- **B**: 멀티턴 입력창, `thread_id` 보존
- **C**: LangGraph 체크포인터(InMemorySaver), refine 노드, 재조정 프롬프트
- **D/E**: 시나리오 데이터 3~5건을 `data/scenarios/`에 적재 (KPI 1~5 대응)

**합격 기준**:
- [ ] 같은 세션에서 두 번째 메시지("화요일 빼줘")가 첫 번째 추천을 기억함
- [ ] `data/scenarios/` 파일 3개 이상

---

### 5/8 (금) — ★ 1차 통합

**그날의 목표**: 사용자 입력부터 화면 출력까지 end-to-end 1회 성공 (Flutter ↔ Supabase / FastAPI ↔ Agent ↔ Tools ↔ Supabase).

전원: 통합 디버깅 집중일. 막히면 즉시 팀 채널에 공유 (필요 시 짧은 화상 통화).

각자:
- **A**: 화면 전체 조립, BE 실연결 검증
- **B**: SSE 청크 5종(text/tool_call/proposal/done/error) 모두 화면 처리, "캘린더에 등록" 버튼(F7) — D의 `create_calendar_event` 호출
- **C**: 실제 LLM(GPT-4o) 호출, ReAct 3단계 로그 확인
- **D/E**: write Tool 안정화, atomic 파일 갱신

**합격 기준**:
- [ ] 채팅창에 "이번 주 운동 추천해줘" 입력 → 좌측 카드 3종 + 추천 슬롯 + 피로도 레이더가 모두 출력
- [ ] 한 번이라도 처음부터 끝까지 끊김 없이 흐름이 돈다

---

### 5/9 (토) — 통합 테스트 + KPI

**그날의 목표**: KPI 시나리오 5개 통과.

각자:
- **A**: 화면 폴리싱(여백, 폰트, 색맹 친화), 로딩/에러 표시
- **B**: 채팅 디자인(말풍선, 이모티콘), SSE 재연결 처리
- **C**: 그래프 디버깅, KPI 자동화(`pytest -m kpi`)
- **D/E**: 시나리오 입력 데이터 vs 기대 응답 매칭 정밀화, 프롬프트 튜닝

**합격 기준**:
- [ ] `pytest -m kpi` 5개 시나리오 모두 통과
- [ ] 1번: 10회 생성 시 충돌 0회
- [ ] 2번: 피로도 높음 부위 추천 0회
- [ ] 5번: 추천 부위와 FE 레이더 색상 일치

---

### 5/10 (일) — 코드 동결

**그날의 목표**: 데모 시나리오 무사고 시연 1회, 태그 `v1.0-demo`.

각자:
- **A**: 데모 화면 최종 점검 (해상도, 컬러, 로딩 상태)
- **B**: 데모 채팅 시나리오 5종 무사고 확인
- **C**: 데모 멘트 페르소나 톤 일관성, 회귀 테스트
- **D**: 데모용 calendar/workouts 데이터 점검
- **E**: 데모용 health/scenarios 데이터 점검

**합격 기준**:
- [ ] 데모 시나리오 1회를 처음부터 끝까지 무사고로 시연
- [ ] git tag `v1.0-demo` 생성, main에 push

---

## 4. 5/11~14 (발표 준비)

기획서 로드맵 그대로.

- 5/11~12: 발표 자료 작성, 데모 스크립트화, 화면 녹화
- 5/13~14: 내부 리허설, 피드백 반영, 데모 환경 최종 점검
- 5/15: 발표

---

## 5. 협업 룰 (요약)

- **회의 없음** — 비동기 협업. 일상 작업은 본인 판단, 인터페이스 변경은 PR로만.
- **Git**: `main` 보호, 브랜치는 `feat/<A~E>-<짧은설명>`, 셀프 머지 금지, 리뷰어 1명 이상 승인 필요
- **인터페이스 변경**: PR 제목에 `[interface-change]` 태그 + 5명 모두 react 후 머지 (`schemas/models.py`·Tool 시그·REST·SSE 청크)
- **머지 충돌 가능성**: 같은 파일 동시 작업 시 PR 코멘트로 순서 합의 (먼저 올린 사람 머지 우선)
- **시크릿**: `.env` 절대 커밋 금지. 새 키는 `.env.example`에 키 이름만 추가.
- **공유 채널**: 팀 카톡/디스코드 + GitHub PR 리뷰

---

## 6. 기술 스택 요약

- **Backend**: Python 3.11+ / FastAPI / uvicorn / sse-starlette / LangGraph(+LangChain) / OpenAI GPT-4o / Pydantic v2
- **Frontend**: Flutter Web (Dart)
- **데이터**: Supabase (PostgreSQL). `data/*.json`은 시딩 입력용, `data/scenarios/*.json`은 KPI 시나리오 정의용.
- **메모리**: LangGraph 체크포인터 (InMemorySaver, 시간 남으면 SqliteSaver)

---

## 7. 자주 묻는 질문

**Q. "역할 분담"이 뭐예요?**
A. 한 사람이 한 영역(FE 대시보드 / FE 채팅 / Agent / Tool)을 풀스택으로 책임진다는 뜻. 예를 들어 D는 calendar 데이터 JSON, CRUD Tool, FastAPI 라우터 위임, 시나리오, 프롬프트 튜닝까지 다 본다. `plan.md` 원본 참조.

**Q. "Mock-first"가 뭐예요?**
A. 다른 사람 코드 기다리지 말고 가짜 데이터로 먼저 돌리라는 뜻. 예를 들어 A는 BE가 501을 돌려도 UI 로딩 상태로 화면을 먼저 만든다. 5/8에 진짜 응답으로 갈아끼우면 됨.

**Q. 회의가 없는데 의견 충돌은 어떻게 해결하나요?**
A. 인터페이스 변경(`schemas`, Tool 시그, REST, SSE)이면 PR에 `[interface-change]` 태그 + 5명 모두 react 후 머지. 일상 작업은 본인 판단으로 진행, 막히면 GitHub Issue 또는 팀 채널.

**Q. "인터페이스 락"이 뭐예요?**
A. REST 엔드포인트, Tool 함수 시그니처, SSE 청크 포맷을 미리 정해놓고 그 후엔 마음대로 바꾸지 않는다는 뜻. 안 그러면 한 명이 시그니처 바꾸면 나머지가 다 깨진다. 변경이 꼭 필요하면 `[interface-change]` PR + 5명 react 후 한 PR로.

**Q. PR 사이즈는 어느 정도가 적당한가요?**
A. 함수 1~2개 또는 엔드포인트 1개 단위. `[tools] create_calendar_event 구현` 같은 단일 책임 PR이 이상적. 한 PR에 100줄 넘으면 쪼갤 수 있는지 검토.

**Q. LLM 호출은 누가 하나요?**
A. `agent/nodes.py`에서만. 다른 모듈(특히 `backend/api/chat.py`)에서 OpenAI 직접 호출 금지. 이렇게 모아두면 키 관리도 한 곳, 디버깅도 한 곳.
