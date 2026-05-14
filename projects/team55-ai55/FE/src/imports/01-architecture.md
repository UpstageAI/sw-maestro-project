# 01. 시스템 아키텍처

## 1. 컴포넌트 구성도

```
┌──────────────────────────────────────────────┐
│  Frontend (React or Next.js)                  │
│   - 프로젝트/Task 입력 폼                       │
│   - 마일스톤·우선순위·일정안 승인 UI               │
│   - 내부 캘린더 (Week / Day 그리드)               │
│   - localStorage: projects, tasks, members,    │
│                   internal_calendar_events     │
└────────────────┬─────────────────────────────┘
                 │ HTTPS / JSON (REST)
                 ▼
┌──────────────────────────────────────────────┐
│  Backend API Gateway (FastAPI)                │
│   - DTO 검증 (Pydantic v2)                     │
│   - 세션ID(=project_id) 단위 캐싱               │
│   - LangGraph super-graph 오케스트레이션         │
│   - Upstage API 키 관리 + rate limit            │
└──┬──────────────┬──────────────┬─────────────┘
   │              │              │
   ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌────────────┐
│ Priority     │ │ Schedule     │ │ Risk       │
│ Agent        │ │ Agent        │ │ Agent      │
│              │ │              │ │            │
│ - Task 분해   │ │ - 슬롯 후보   │ │ - Binary   │
│   (LLM)      │ │   생성 (룰)   │ │   checks   │
│ - 결정적 점수  │ │ - 충돌 검사   │ │   (룰)      │
│   함수       │ │   (룰)        │ │ - 과부하    │
│ - LLM        │ │ - 우선 슬롯   │ │   탐지      │
│   Narrator   │ │   선정 (룰)   │ │ - LLM      │
│              │ │              │ │   Narrator │
└──────┬───────┘ └──────┬───────┘ └─────┬──────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │ External / Local        │
            │ - Upstage API (LLM)     │
            │ - Frontend localStorage │
            │   (영속화 - 서버 DB 없음) │
            └─────────────────────────┘
```

서버는 stateless. **모든 영속 상태는 Frontend localStorage에** 있고, Backend는 요청마다 전체 프로젝트 상태(projects, members, tasks, calendar_events)를 받아 분석 후 추천만 반환한다 — 이 결정은 원본 기획서 167~177행의 시스템 워크플로우와 일치한다.

## 2. 요청 흐름 (Sequence)

기획서 §2의 "Agent가 스스로 수행하는 일 6가지"와 "PM 승인이 필요한 일 2가지"를 그래프 흐름으로 매핑.

```
사용자 시나리오                     ↔  시스템 호출
─────────────────────────────────────────────────────────
1. 프로젝트/팀원/근무가능시간 입력      → POST /v1/projects (저장만)
2. AI 마일스톤 제안 요청               → POST /v1/projects/{id}/milestones:suggest
   - LLM 1회: 프로젝트 목표 → 마일스톤 후보 5~8개
3. PM이 마일스톤 수정/승인 [G1]        → POST /v1/projects/{id}/milestones:approve
4. PM이 Task 입력                     → POST /v1/projects/{id}/tasks (CRUD)
5. AI 분석 트리거                     → POST /v1/projects/{id}/analyze
   ├─ priority_subgraph: Task 분해 + 우선순위 점수
   ├─ schedule_subgraph: 슬롯 후보 생성 + 충돌 검사
   └─ risk_subgraph: binary checks + 과부하 탐지
6. PM이 슬롯/추천 수정 + 승인 [G2]      → POST /v1/projects/{id}/schedule:approve
   ↳ 응답에 명시 승인된 events 만 포함됨, Frontend가 localStorage 캘린더에 INSERT
7. Task 상태/진척률 변경 시 재분석       → POST /v1/projects/{id}/analyze (멱등 캐시 무효화)
```

LLM 호출 수: **마일스톤 제안 1회 + 분석 시 평균 4회 (Priority Narrator 1 + Schedule Reranker 1 + Risk Soft Checks 1 + Risk Narrator 1, Task 분해는 PM이 요청한 task 수만큼 추가)**. fallback/skip 조건 충족 시 그보다 적게 호출됨.

## 3. Agent 분담 원칙

| Agent | Agentic 패턴 | LLM 사용 | 결정성 |
|---|---|---|---|
| Priority Agent | **Decompose-and-Score**: Task 분해(LLM) + 5요소 가중합(결정적) + Narrator(LLM) | 분해 0~N회 + Narrator 1회 (`temperature=0`) | 점수 100% 결정적, 분해/설명은 schema 강제 |
| Schedule Agent | **Floor + Reranker**: 결정적 후보 생성/검증(룰) + LLM Reranker(t=0) + verify_rerank 안전망 | Reranker 1회 (조건 충족 시) | 슬롯 multiset/datetime 100% 결정적, **순서만** LLM |
| Risk Agent | **Hard + Soft Lane**: 16개 결정적 체크 + LLM Soft Checks(t=0.2, 5종) + Narrator(LLM, t=0) | Soft 1회 + Narrator 1회 | hard checks 100% 결정적, soft는 별도 영역 + verify로 환각 차단 |

**핵심:**
1. **결정적 floor가 모든 안전 보장을 책임진다** — 슬롯 충돌, blocker, snapshot_hash, schema validation은 LLM이 어떻게 동작해도 깨지지 않는다.
2. **LLM은 결정적 룰이 못 잡는 의미·맥락 영역에서만 가치를 더한다** — Task 분해, 슬롯 재정렬, 텍스트 기반 위험 추론, 자연어 설명.
3. 평균 LLM 호출 ~4회/세션 (분해 0회 기준). 모든 LLM 출력은 자체 verifier를 통과해야 응답에 포함된다.

## 3.1 LangGraph 채택 (전역)

본 프로젝트의 모든 Agent와 Backend 오케스트레이터는 **LangGraph StateGraph**로 구현한다.

| 계층 | LangGraph 역할 |
|---|---|
| 각 Agent (Priority / Schedule / Risk) | 자체 sub-graph (StateGraph). 노드 = 결정적 도구 또는 LLM 호출. 조건부 엣지로 분기 표현. |
| Backend 오케스트레이터 | super-graph. Agent sub-graph 3개를 노드로 받아 병렬/직렬 흐름을 구성. |
| 관측성 | LangSmith trace 통합 (선택, 환경변수). 노드별 latency / token / 입출력 자동 기록. |

### 이점
1. 각 Agent의 **state, 분기, 루프**가 spec과 코드에서 동일한 시각으로 표현됨 (그림 ↔ Python 일치)
2. Schedule Agent의 "후보 → 충돌 검사 → 폐기 → 재생성" 루프, Priority Agent의 "Task 분해 검증 실패 → 재호출" 루프가 LangGraph 정통 사용처
3. Checkpoint 기능으로 디버깅 재현성 확보 (동일 state 재실행 가능)
4. 각 Agent의 단일 책임이 노드 단위로 강제됨 (한 노드 = 한 도구 OR 한 LLM 호출)

### 결정적 보장
- LangGraph 자체는 결정성을 깨지 않는다. 노드는 순수 함수 또는 LLM(`temperature=0`).
- 본 spec의 모든 결정적 룰(우선순위, 슬롯 충돌, 리스크 체크)은 LangGraph 노드 안에서 동일하게 결정적으로 동작.

### 구현 표준
- LangGraph 0.2+ (Python). `langgraph.graph.StateGraph` 사용.
- 모든 sub-graph는 `compile()` 결과를 export. super-graph가 이를 import.
- State는 Pydantic v2 모델 (`07-data-contracts.md` schema와 일관).
- 각 노드는 단일 책임 (한 가지 도구 호출 또는 한 가지 LLM 호출).

### Super-graph 흐름 (Backend가 정의)

```
[START]
   │
   ▼
[load_project_snapshot]   ← 결정적 (요청 본문 → 정규화)
   │
   ▼
[priority_subgraph]       ← Task 분해 + 우선순위 점수 (Agent sub-graph)
   │
   ├──parallel──┐
   ▼            ▼
[schedule_subgraph]  [risk_subgraph]    ← Agent sub-graph (병렬)
   │            │
   └────join────┘
                │
                ▼
[pack_response]   ← 결정적 (AnalyzeResponse 패키징)
                │
                ▼
[END]
```

Schedule는 priority 결과의 `priority_score`로 슬롯 배치 우선순위를 결정하므로 priority 다음에 실행. Risk는 priority의 결과(예: progress_gap)와 schedule의 결과(예: 마감 후 배치 여부)를 모두 사용하므로 두 sub-graph 결과를 입력으로 받는다 — **단, MVP에서는 Risk를 schedule과 병렬 실행하고 schedule 결과 일부만 사용해 단순화**한다 (구현 비용 트레이드오프).

## 4. 디렉토리 레이아웃 (제안)

```
ai-swm-55/
├── docs/specs/                # 본 spec 디렉토리
├── frontend/                  # React or Next.js (Frontend 담당)
│   ├── src/
│   │   ├── pages/             # /projects, /projects/[id], /projects/[id]/calendar
│   │   ├── components/
│   │   ├── api/               # 자동생성 OpenAPI client
│   │   ├── store/             # localStorage adapter
│   │   └── lib/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI 라우터 (Backend 담당)
│   │   ├── agents/
│   │   │   ├── priority/      # Priority Agent (담당자 1)
│   │   │   ├── schedule/      # Schedule Agent (담당자 2)
│   │   │   └── risk/          # Risk Agent (담당자 3)
│   │   ├── schemas/           # Pydantic 모델 (07-data-contracts 기준)
│   │   ├── scoring/           # 결정적 우선순위 / 충돌 검사 모듈
│   │   │   ├── priority.py
│   │   │   ├── slot_packing.py
│   │   │   └── risk_checks/   # 체크별 1파일
│   │   └── services/
│   │       ├── llm_client.py  # Upstage API wrapper
│   │       └── id_minter.py
│   ├── tests/
│   │   ├── fixtures/          # 골든 입력 + 기대 JSON
│   │   ├── test_priority.py
│   │   ├── test_schedule.py
│   │   ├── test_risk.py
│   │   └── test_e2e.py
│   └── pyproject.toml
└── README.md
```

## 5. 데이터 흐름 보장

### 5.1 멱등성
- `analyze` 요청은 (project_state hash) 단위로 캐싱한다. 같은 hash 재요청 시 LLM 재호출 없이 캐시 결과 반환.
- Task 1개라도 변경되면 hash 변경 → 새 분석.

### 5.2 실패 처리

원본 기획서 "제약사항 및 예외 처리" 5개 항목과 1:1 매핑.

| 단계 | 실패 유형 | 대응 |
|---|---|---|
| Task 입력 | 마감기한, 예상 소요시간, 중요도 누락 | 422 + 입력 보완 요청 메시지 (기획서 §4 "Task 정보 부족") |
| Task 의존성 | 순환 의존 발견 (DAG 위반) | Risk `dependency_correctness` fail + 순환 경로/해소 제안 노출 |
| Priority Agent | LLM 분해 schema 위반 | 재시도 2회 → 실패 시 Task를 분해 안 함 + warning |
| Priority Narrator | LLM 텍스트 누락/형식 위반 | 룰 기반 fallback 템플릿 (기획서 §4 "LLM 설명이 비어있거나 형식이 맞지 않는 경우") |
| Schedule Agent | 가능 슬롯 0개 (근무가능시간 < 예상 소요) | warning + Task 보존 + 캘린더 미반영 |
| Schedule Agent | 선행 Task 미완료 | 후행 Task 슬롯 배치 거부 + warning 표시 (기획서 §4) |
| Risk Agent | 데이터 부족(진척률 누락) | 해당 체크 not_applicable 처리 |
| Upstage API | 4xx/5xx | 재시도 1회 → 실패 시 결정적 산출물만 반환 (점수/슬롯), Narrator는 fallback |
| Approval gate G2 | 만료된 슬롯 후보 (캐시 hash 변경) | 409 Conflict + 재분석 안내 |

### 5.3 관측성 (Observability)
- 모든 Agent 호출은 다음을 로깅한다.
  - `project_id`, `agent_name`, `latency_ms`, `tokens`, `schema_pass`, `cache_hit`
- LLM 호출은 raw response를 7일간 보관 (디버깅 + 회귀 테스트 골든 셋 후보).

## 6. 보안 / 프라이버시

- 본 시스템은 PII를 최소화한다: Task 내용은 PM이 직접 입력하므로 PM의 책임 영역.
- 팀원 정보: 이름 + 역할만 (이메일/연락처 미수집 — MVP).
- LLM 프롬프트에 팀원 실명 포함 가능하지만, Upstage API에 전송되는 페이로드는 라우트 로그에서 7일 후 자동 삭제.
- 외부 캘린더 OAuth 토큰: **본 MVP는 미사용** (Google Calendar 연동 자체 제외).
- localStorage 데이터는 사용자 브라우저에만 존재 — 사용자가 브라우저 데이터 지우면 모든 정보 손실 (FE에 export/import 기능 제공).

## 7. 비-목표 (시스템 차원)

- 다중 사용자 인증 / 권한 (MVP는 단일 PM 세션)
- 학습 / 파인튜닝 (모든 추론은 zero-shot + 룰)
- 실시간 협업 (멀티유저 동시 편집 X — localStorage 단일 브라우저)
- 모바일 네이티브 앱
- 외부 알림 (Slack, 이메일, push)
- 외부 캘린더 양방향 동기화 (원본 기획서 84,96행 명시 제외)
