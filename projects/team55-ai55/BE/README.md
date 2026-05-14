# Make AI Agent Backend

PM 일정 관리 assistant를 위한 FastAPI backend MVP입니다. Backend는
`ProjectSnapshot`을 받아 priority, schedule, risk agent를 실행한 뒤,
frontend가 바로 사용할 수 있는 하나의 분석 결과를 반환합니다.

## API 변경 판단

현재 3명 분업 구조에서는 BE API를 크게 바꿀 필요가 없습니다.

이미 중요한 경계는 잡혀 있습니다.

- `/v1/projects/{project_id}/analyze`는 메인 super-graph endpoint입니다.
  `priority -> schedule -> risk` 순서로 실행하고 하나의 `AnalyzeResponse`를
  반환합니다.
- `/v1/projects/{project_id}/schedule:approve`는 PM 승인 endpoint입니다.
  기존 `snapshot_hash` 기준으로 승인된 내부 캘린더 이벤트 객체를 만듭니다.
- `/v1/projects/{project_id}/risk:simulate`는 risk 제안을 적용했을 때
  snapshot이 실제로 개선되는지 미리 보는 endpoint입니다.
- milestone endpoint는 분석 흐름이 아니라 프로젝트 세팅 흐름이므로 별도로
  두는 게 맞습니다.

따라서 agent를 병렬로 구현하는 동안 public API는 최대한 안정적으로 유지하는
방향이 좋습니다. 각 담당자는 본인 agent module과 꼭 필요한 shared schema만
수정하는 것을 기본으로 합니다.

새 public endpoint는 frontend에 명확히 별도 사용자 액션이 생겼고, 그 액션이
기존 `analyze`, `schedule:approve`, `risk:simulate` 흐름으로 표현되지 않을 때만
추가합니다.

## 현재 Public Endpoints

| Endpoint | 역할 | 주 담당 |
|---|---|---|
| `GET /v1/health` | Backend, Upstage, LLM, agent 상태 확인 | 공통 |
| `POST /v1/projects` | `project_id`가 붙은 project 객체 생성 | 공통 |
| `POST /v1/projects/{project_id}/milestones:suggest` | milestone 초안 제안 | 공통 / 세팅 |
| `POST /v1/projects/{project_id}/milestones:approve` | 승인된 milestone 초안을 실제 milestone 객체로 변환 | 공통 / 세팅 |
| `POST /v1/projects/{project_id}/analyze` | priority, schedule, risk agent를 한 번에 실행 | 3명 공통 |
| `POST /v1/projects/{project_id}/schedule:approve` | 선택된 schedule slot을 내부 캘린더 이벤트 객체로 승인 | Schedule 담당 |
| `POST /v1/projects/{project_id}/risk:simulate` | 선택한 risk 제안을 적용했을 때 before/after 비교 | Risk 담당, Priority 의존 |

## FE에서 API가 호출되는 위치

FE는 page component에서 raw `fetch`를 직접 호출하지 않고,
`FE/src/app/apiClient.ts`의 wrapper를 통해 BE API를 호출합니다. BE API를 바꿀
때는 endpoint route만 보지 말고 아래 FE wrapper와 화면 흐름을 같이 확인해야
합니다.

| BE endpoint | FE wrapper | 실제 호출 위치 | 사용자 액션 |
|---|---|---|---|
| `POST /v1/projects` | `createProject(project)` | `FE/src/app/pages/NewProject.tsx`의 `generateMilestones()` | 새 프로젝트 Step 2에서 "마일스톤 생성"을 누를 때, BE 기준 `project_id`를 먼저 발급 |
| `POST /v1/projects/{project_id}/milestones:suggest` | `suggestMilestones(project)` | `FE/src/app/pages/NewProject.tsx`의 `generateMilestones()` | 발급된 `project_id`로 milestone 후보를 받아 Step 3에 표시 |
| `POST /v1/projects/{project_id}/milestones:approve` | `approveMilestones(project)` | `FE/src/app/pages/NewProject.tsx`의 `handleFinish()` | Step 3에서 선택/수정한 milestone을 G1 승인 상태로 확정하고 localStorage project에 저장 |
| `POST /v1/projects/{project_id}/analyze` | `analyzeProject(project, requestDecompositionFor)` | `FE/src/app/pages/Dashboard.tsx`의 `runAnalysisForProject()` | Dashboard의 AI 분석 재실행, stale 자동 재분석, Priority 탭의 선택 Task 분해 요청 |
| `POST /v1/projects/{project_id}/schedule:approve` | `approveProjectSchedule(project, result, selectedTaskIds, analysisFingerprint)` | `FE/src/app/pages/Dashboard.tsx`의 `approveSelectedSchedule()` | Schedule 탭에서 선택한 추천 slot을 G2 승인하고 `events_created`를 localStorage calendar event로 저장 |
| `POST /v1/projects/{project_id}/risk:simulate` | `simulateRiskSuggestion(project, suggestionId)` | `FE/src/app/pages/Dashboard.tsx`의 `simulateSuggestion()` | Risk 탭에서 개별 suggestion의 적용 전/후 개선 여부를 미리 표시 |

FE 쪽 핵심 파일:

- `FE/src/app/generated/openapi.ts`: FastAPI OpenAPI에서 생성된 path/type입니다.
  직접 수정하지 않습니다.
- `FE/src/app/apiClient.ts`: BE request payload 생성, response mapping, error
  mapping을 담당합니다.
- `FE/src/app/analysisTypes.ts`: Dashboard에서 쓰는 UI용 분석 결과 type입니다.
- `FE/src/app/store.tsx`: project/member/task/milestone/calendar event를
  localStorage에 저장하는 FE 상태 모델입니다.
- `FE/src/app/pages/NewProject.tsx`: project 생성과 milestone G1 승인 흐름입니다.
- `FE/src/app/pages/Dashboard.tsx`: analyze, schedule G2 승인, risk simulation
  흐름입니다.

### FE 호출 흐름별 주의점

`POST /v1/projects`

- FE는 새 프로젝트 생성 중 임시 project id를 쓰다가, milestone 생성 직전에 BE가
  발급한 `project_id`로 교체합니다.
- `ProjectCreate` request shape을 바꾸면 `createProject()`의 body mapping도 같이
  수정해야 합니다.

`POST /v1/projects/{project_id}/milestones:suggest`

- FE는 `buildSnapshotForApi(project)`와 `max_milestones: 8`을 보냅니다.
- 응답의 `proposed_milestones`는 FE의 `Milestone[]`로 변환되어 Step 3 화면에
  표시됩니다.

`POST /v1/projects/{project_id}/milestones:approve`

- FE는 archived가 아닌 milestone만 `approved` 배열로 보내고, archived 수는
  `rejected_count`로 보냅니다.
- 응답의 `milestones`가 localStorage project의 승인된 milestone 목록이 됩니다.

`POST /v1/projects/{project_id}/analyze`

- FE는 매번 전체 `ProjectSnapshot`을 보냅니다. BE가 project/task/calendar 상태를
  장기 저장한다고 가정하면 안 됩니다.
- FE가 보내는 options는 현재 `request_decomposition_for`,
  `schedule_horizon_days: 14`, `include_unscheduled_in_response: true`입니다.
- 응답의 `snapshot_hash`는 schedule 승인에 필요합니다.
- 응답 shape을 바꾸면 `mapAnalyze()`, `analysisTypes.ts`, Dashboard tab UI를 같이
  확인해야 합니다.

`POST /v1/projects/{project_id}/schedule:approve`

- FE는 `/analyze` 응답의 `snapshot_hash`와 선택된 `task_id`,
  `candidate_slot_index`, 선택적 override 시간을 보냅니다.
- FE는 `analysisFingerprint`로 현재 project가 분석 당시와 달라졌는지 먼저
  확인합니다. 달라졌으면 승인하지 않고 재분석합니다.
- BE가 반환한 `events_created`만 FE `CalendarEvent[]`로 변환되어 localStorage에
  저장됩니다. `events_rejected`는 사용자에게 오류로 보여줍니다.

`POST /v1/projects/{project_id}/risk:simulate`

- FE는 현재 `ProjectSnapshot`과 `applied_suggestion_ids` 하나를 보냅니다.
- 응답은 suggestion별 `simulationBySuggestion` 상태로 저장되어 Risk panel에
  표시됩니다.
- `RiskSuggestion` 또는 `score_action_coherence` shape을 바꾸면 Risk panel 표시
  로직도 같이 수정해야 합니다.

## Agent별 담당 범위

### 1. Priority 담당

주요 파일:

- `app/agents/priority.py`
- DAG, dependency, task 공통 helper가 필요하면 `app/agents/common.py`
- priority 관련 schema는 `app/schemas.py`
- priority 관련 테스트는 `tests/test_backend_contracts.py`

해야 할 일:

- scoring 전에 task dependency 구조를 검증합니다. 순환 dependency는
  `/analyze` 요청 단위의 에러로 유지합니다.
- 모든 task의 priority score를 결정적으로 계산합니다.
- `todo` / `in_progress` 상태이고 담당자가 없는 task는 역할 단서와 현재 부하를
  기준으로 담당자를 배정하고 `task_assignments`에 기록합니다.
- `factors`, `evidence_facts`, `rank`, `rationale`로 점수 근거가 설명되게
  유지합니다.
- `AnalyzeOptions.request_decomposition_for`에 들어온 task에 대해 선택적으로
  task decomposition을 지원합니다.
- LLM은 decomposition과 narration에만 사용합니다. 실제 priority score 계산은
  결정적 로직이어야 합니다.
- decomposition이나 narration이 fallback될 때 warning이 명확해야 합니다.

하면 안 되는 일:

- task의 `importance`, `estimated_hours`, status, schedule을 바꾸지 않습니다.
- 이미 담당자가 있는 task의 assignee는 바꾸지 않습니다.
- decomposition 결과를 바로 실제 task로 생성하지 않습니다.
- calendar slot이나 risk level을 결정하지 않습니다.

Handoff:

- `PriorityResponse`를 반환합니다.
- Schedule은 `tasks_priority`의 task id와 정렬 결과에 의존합니다.
- Risk는 score, rank, evidence를 사용해 blocker와 risk 설명을 만듭니다.

### 2. Schedule 담당

주요 파일:

- `app/agents/schedule.py`
- schedule 승인 로직은 `app/api/routes.py`
- schedule 관련 schema는 `app/schemas.py`
- schedule 관련 테스트는 `tests/test_backend_contracts.py`

해야 할 일:

- `ProjectSnapshot`과 `PriorityResponse`를 입력으로 받습니다.
- `estimated_hours`와 `assignee_id`가 있는 active task에 대해 후보 slot을
  생성합니다.
- 근무 가능 시간, 기존 approved/external blocking event, predecessor 순서,
  deadline, `AnalyzeOptions.schedule_horizon_days`를 지킵니다.
- `SlotProposal`에 안정적인 candidate slots, `selected_index`, `fit_score`,
  `quality`, conflicts, rationale facts를 채워 반환합니다.
- 배치 불가능한 task는 조용히 누락하지 말고 `unschedulable` reason으로
  명시합니다.
- LLM reranking은 이미 검증된 candidate slot 중 하나를 고르는 정도로만
  제한합니다.

하면 안 되는 일:

- `/analyze` 중에 calendar event를 insert하지 않습니다.
- LLM이 slot datetime을 만들거나, 삭제하거나, 수정하게 두지 않습니다.
- task를 재배정하거나 누락된 estimated_hours를 임의로 만들지 않습니다.
- hard conflict를 숨기지 않습니다.

Handoff:

- `ScheduleResponse`를 반환합니다.
- Risk는 schedule proposal을 사용해 deadline, dependency, workload check를
  평가합니다.
- `/schedule:approve`는 `/analyze`의 `snapshot_hash`와 선택된 candidate index를
  사용해 `InternalCalendarEvent` 객체를 만듭니다.

### 3. Risk 담당

주요 파일:

- `app/agents/risk.py`
- risk simulation 로직은 `app/api/routes.py`
- risk 관련 schema는 `app/schemas.py`
- risk 관련 테스트는 `tests/test_backend_contracts.py`

해야 할 일:

- `ProjectSnapshot`, `PriorityResponse`, 필요하면 `ScheduleResponse`를 입력으로
  받습니다.
- deadline, dependency, workload, data health 영역의 hard check를 결정적으로
  평가합니다.
- `blockers_failed`, `task_risk_levels`, `member_workload`, 실행 가능한
  `suggestions`를 반환합니다.
- LLM soft check는 hard check와 분리합니다. 텍스트 패턴을 의심할 수는 있지만
  blocker status나 risk level을 덮어쓰면 안 됩니다.
- 모든 suggestion은 실패한 check id와 허용된 action vocabulary에 연결되어야
  합니다.
- `/risk:simulate`를 유지해서 frontend가 선택한 suggestion이 risk와 priority
  coherence를 실제로 개선하는지 미리 볼 수 있게 합니다.

하면 안 되는 일:

- 멤버의 성격, 태도, 역량을 평가하지 않습니다.
- task, assignee, predecessor, calendar event를 직접 변경하지 않습니다.
- soft check를 확정 사실처럼 다루지 않습니다.
- MVP 범위에서 외부 데이터 소스를 추가하지 않습니다.

Handoff:

- `RiskResponse`를 반환합니다.
- Frontend는 hard blocker, task risk level, member workload, soft check,
  suggestion을 서로 다른 개념으로 표시해야 합니다.
- Simulation은 선택된 `RiskSuggestion.id`를 받아 before/after risk 상태를
  반환합니다.

## 공통 규칙

- `app/schemas.py`는 공유 contract입니다. 변경하면 FE generated type, tests,
  세 agent 모두에 영향이 갑니다.
- 분석 입력은 `ProjectSnapshot` 하나로 유지합니다. MVP backend는 장기 project
  persistence를 소유하지 않습니다.
- `snapshot_hash`는 안정적으로 유지해야 합니다. 승인 endpoint는 오래되었거나
  없는 분석 결과를 거절해야 합니다.
- Public API response는 frontend가 바로 쓰기 좋은 형태여야 합니다. 내부 디버깅용
  필드는 꼭 필요할 때만 `meta`에 넣습니다.
- 결정적 로직은 `UPSTAGE_API_KEY` 없이도 통과해야 합니다. LLM 경로는 반드시
  결정적 fallback을 가져야 합니다.
- agent response shape을 바꾸면 함께 업데이트해야 할 것:
  - `app/schemas.py`
  - `tests/test_backend_contracts.py`
  - OpenAPI generation flow를 통한 `FE/src/app/generated/openapi.ts`
  - generated API type을 감싸는 frontend type

## 구현 순서

1. 각 담당자는 먼저 본인 agent module을 수정합니다.
2. response shape 변경이 필요하면 같은 change에서 `app/schemas.py`와 테스트를
   같이 수정합니다.
3. `BE/`에서 backend test를 실행합니다.
4. OpenAPI가 바뀌었으면 repo root에서 FE API type을 재생성합니다.
5. API contract가 안정된 뒤 frontend와 연결합니다.

## 실행

```bash
cd BE
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/v1/health
```

## Upstage

`BE/.env.example`을 `BE/.env`로 복사한 뒤 `UPSTAGE_API_KEY`를 설정하면 실제
Upstage LLM 호출을 사용할 수 있습니다.

```env
UPSTAGE_API_KEY=your_upstage_api_key_here
UPSTAGE_BASE_URL=https://api.upstage.ai/v1
UPSTAGE_MODEL=solar-mini
LLM_DAILY_BUDGET=500
LLM_MAX_CONCURRENCY=5
RATE_LIMIT_PER_MIN=30
FRONTEND_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

`UPSTAGE_API_KEY`가 없으면 backend는 local development와 test를 위해 결정적
fallback output을 사용합니다. key가 있으면 milestone suggestion, priority
narration/decomposition, schedule reranking, risk soft check가 Upstage의
OpenAI-compatible chat completions API인 `/chat/completions`를 호출합니다.

`LLM_DAILY_BUDGET`은 local call guard입니다. 예산을 다 쓰면 network를 호출하지
않고 결정적 fallback output을 반환합니다. `LLM_MAX_CONCURRENCY`는 동시에 실행할
수 있는 Upstage 요청 수를 제한합니다.

`RATE_LIMIT_PER_MIN`은 local API guardrail입니다. 기본값은 backend spec의
30 req/min IP 제한을 따릅니다. local QA를 많이 돌릴 때만 임시로 올립니다.

`FRONTEND_ORIGINS`는 CORS allowlist입니다. 기본값은 local Vite port `5173`의
`localhost`와 `127.0.0.1`을 허용합니다.

Network 호출 없이 local readiness를 확인하려면:

```bash
npm run check:upstage-ready
```

`BE/.env` 설정 후 실제 Upstage 요청을 확인하려면:

```bash
PYTHONPATH=BE BE/.venv/bin/python scripts/check_upstage_readiness.py --require-key --live
```

## 테스트

```bash
cd BE
.venv/bin/python -m pytest
```
