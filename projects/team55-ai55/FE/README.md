# PM Agent Frontend

PM 일정 관리 Agent MVP의 React/Vite 프론트엔드입니다.

이 README는 FE 담당자가 Backend API를 보면서 수정할 수 있도록 만든 인수인계 문서입니다. 현재 Backend는 stateless 구조입니다. 프로젝트, 멤버, Task, 마일스톤, 승인된 캘린더 데이터는 FE `localStorage`에 있고, API 요청마다 전체 `ProjectSnapshot`을 보내 추천 결과나 승인된 이벤트 객체를 받습니다.

## 로컬 실행

레포 루트에서 Backend를 먼저 실행합니다.

```bash
npm run dev:be
```

그다음 Frontend를 실행합니다.

```bash
npm run dev:fe
```

기본 로컬 포트는 아래와 같습니다.

- FE: `http://127.0.0.1:5173`
- BE: `http://127.0.0.1:8000`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/v1/health`

`FE/` 폴더 안에서 직접 실행할 때는 아래 명령을 사용합니다.

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173
```

FE 포트를 바꿔서 실행한다면 `BE/.env`의 `FRONTEND_ORIGINS`에 해당 origin을 추가해야 합니다.

## API 계약 확인 순서

API를 보면서 FE를 수정할 때는 아래 순서로 보면 됩니다.

- `../docs/specs/07-data-contracts.md`: schema 기준 문서입니다.
- `../docs/specs/05-backend-spec.md`: Backend endpoint와 승인 게이트 동작을 설명합니다.
- `../BE/app/api/routes.py`: 실제 FastAPI route 구현입니다.
- `src/app/generated/openapi.ts`: FastAPI OpenAPI에서 생성된 TypeScript 타입과 `openApiPaths`입니다. 직접 수정하지 않습니다.
- `src/app/apiClient.ts`: snapshot 생성, endpoint 호출, 응답 매핑, 에러 매핑을 담당하는 FE API adapter입니다.
- `src/app/analysisTypes.ts`: Dashboard에서 쓰는 UI용 분석 결과 타입입니다.
- `src/app/store.tsx`: localStorage 모델과 export/import 로직입니다.

## 현재 API 래퍼

페이지 컴포넌트에서 raw `fetch`를 직접 만들지 말고 `src/app/apiClient.ts`의 래퍼를 사용합니다.

| Wrapper | Endpoint | 호출 위치 | 사용자 기능 |
|---|---|---|---|
| `createProject(project)` | `POST /v1/projects` | `src/app/pages/NewProject.tsx` `generateMilestones()` | 새 프로젝트 Step 2에서 "마일스톤 생성"을 누를 때, Backend 계약에 맞는 `project_id`를 먼저 발급 |
| `suggestMilestones(project)` | `POST /v1/projects/{id}/milestones:suggest` | `src/app/pages/NewProject.tsx` `generateMilestones()` | 발급된 `project_id`로 G1 마일스톤 후보를 받아 Step 3 화면에 표시 |
| `approveMilestones(project)` | `POST /v1/projects/{id}/milestones:approve` | `src/app/pages/NewProject.tsx` `handleFinish()` | Step 3에서 선택/수정한 마일스톤을 G1 승인 상태로 확정하고 localStorage 프로젝트에 저장 |
| `analyzeProject(project, taskIds)` | `POST /v1/projects/{id}/analyze` | `src/app/pages/Dashboard.tsx` `runAnalysisForProject()` | Dashboard의 "AI 분석 다시 실행", 자동 stale 재분석, Priority 탭의 "선택 Task 분해 요청 [G3]"에서 Priority/Schedule/Risk 분석 실행 |
| `approveProjectSchedule(project, result, selectedIds, fingerprint)` | `POST /v1/projects/{id}/schedule:approve` | `src/app/pages/Dashboard.tsx` `approveSelectedSchedule()` | Schedule 탭에서 선택한 추천 슬롯을 G2 승인하고, Backend가 반환한 `events_created`를 캘린더 이벤트로 저장 |
| `simulateRiskSuggestion(project, suggestionId)` | `POST /v1/projects/{id}/risk:simulate` | `src/app/pages/Dashboard.tsx` `simulateSuggestion()` | Risk 탭에서 "적용 전 시뮬레이션"을 누를 때, 제안 적용 전/후 risk 변화와 우선순위 개선 여부를 미리 표시 |

## API별 수정 포인트

### `POST /v1/projects`

- FE 호출: `src/app/pages/NewProject.tsx`의 `generateMilestones()`
- FE 래퍼: `src/app/apiClient.ts`의 `createProject(project)`
- 사용 시점: 새 프로젝트 생성 flow에서 팀원 입력 후 마일스톤 후보를 만들기 직전
- 하는 일: FE 임시 `proj_` ID 대신 Backend가 발급한 `project_id`를 받아 이후 G1/G2/API 요청 기준 ID로 사용
- 수정할 때 볼 것: `createProject()`의 request body, `ProjectCreate` / `Project` 타입, `NewProject.tsx`의 `setProjectId(resolvedProjectId)`

### `POST /v1/projects/{id}/milestones:suggest`

- FE 호출: `src/app/pages/NewProject.tsx`의 `generateMilestones()`
- FE 래퍼: `src/app/apiClient.ts`의 `suggestMilestones(project)`
- 사용 시점: 새 프로젝트 Step 2에서 "마일스톤 생성" 클릭 후
- 하는 일: `buildSnapshotForApi(project)`와 `max_milestones: 8`을 보내고, 응답의 `proposed_milestones`를 FE `Milestone[]` 형태로 변환
- 화면 반영: Step 3 마일스톤 후보 리스트에 표시하고, 사용자가 제목/날짜를 수정하거나 제외할 수 있음
- 수정할 때 볼 것: Backend `ProposedMilestone` 필드, FE `Milestone` 필드, `suggestMilestones()`의 `map()`

### `POST /v1/projects/{id}/milestones:approve`

- FE 호출: `src/app/pages/NewProject.tsx`의 `handleFinish()`
- FE 래퍼: `src/app/apiClient.ts`의 `approveMilestones(project)`
- 사용 시점: 새 프로젝트 Step 3에서 최종 완료 버튼 클릭 시
- 하는 일: archived가 아닌 마일스톤을 `approved` 배열로 보내고, archived 수는 `rejected_count`로 보냄
- 화면 반영: Backend가 반환한 승인 마일스톤을 localStorage 프로젝트에 저장한 뒤 Dashboard로 이동
- 수정할 때 볼 것: `approveMilestones()`의 `approved` payload, `handleFinish()`의 `addProject()`

### `POST /v1/projects/{id}/analyze`

- FE 호출: `src/app/pages/Dashboard.tsx`의 `runAnalysisForProject()`
- FE 래퍼: `src/app/apiClient.ts`의 `analyzeProject(project, requestDecompositionFor)`
- 사용 시점: "AI 분석 다시 실행" 버튼, 프로젝트 수정 후 stale 자동 재분석, 캘린더 이벤트 이동 후 재분석, Priority 탭의 Task 분해 요청
- 하는 일: 전체 `ProjectSnapshot`과 `options`를 보내 Priority/Schedule/Risk 결과를 한 번에 받음
- 요청 옵션: `request_decomposition_for`, `schedule_horizon_days: 14`, `include_unscheduled_in_response: true`
- 화면 반영: `mapAnalyze()`가 Backend 응답을 `AnalyzeResult`로 바꾸고, Dashboard의 Priority/Schedule/Risk 탭과 `lastAnalysis` 캐시에 저장
- 수정할 때 볼 것: `buildSnapshotForApi()`, `mapAnalyze()`, `analysisTypes.ts`, `Dashboard.tsx`의 `setAnalysis()` / `updateProject(... lastAnalysis ...)`

### `POST /v1/projects/{id}/schedule:approve`

- FE 호출: `src/app/pages/Dashboard.tsx`의 `approveSelectedSchedule()`
- FE 래퍼: `src/app/apiClient.ts`의 `approveProjectSchedule(project, result, selectedTaskIds, analysisFingerprint)`
- 사용 시점: Schedule 탭에서 승인할 Task 슬롯을 선택한 뒤 G2 승인 버튼 클릭 시
- 하는 일: `/analyze` 응답의 `snapshot_hash`와 선택된 `task_id`, `candidate_slot_index`, 선택적 override 시간을 보냄
- 사전 방어: `analysisFingerprint`가 현재 프로젝트 fingerprint와 다르면 FE에서 먼저 `snapshot_hash_stale`로 막고 재분석
- 화면 반영: Backend가 반환한 `events_created`만 FE `CalendarEvent[]`로 변환해 localStorage에 추가하고, `events_rejected`가 있으면 오류 메시지 표시
- 수정할 때 볼 것: `approveProjectSchedule()`의 approvals payload, `toDateInput()` / `toTimeInput()`, `Dashboard.tsx`의 `selectedSchedule`, `chooseScheduleIndex()`, `setScheduleOverride()`

### `POST /v1/projects/{id}/risk:simulate`

- FE 호출: `src/app/pages/Dashboard.tsx`의 `simulateSuggestion()`
- FE 래퍼: `src/app/apiClient.ts`의 `simulateRiskSuggestion(project, suggestionId)`
- 사용 시점: Risk 탭에서 개별 제안의 "적용 전 시뮬레이션" 클릭 시
- 하는 일: 현재 `ProjectSnapshot`과 `applied_suggestion_ids`를 보내 risk suggestion 적용 전/후 결과를 받음
- 화면 반영: `simulationBySuggestion`에 suggestion별 결과를 저장하고, Risk 카드에서 변경된 check와 `score_action_coherence`를 표시
- 수정할 때 볼 것: `RiskSimulationResult`, `RiskPanel`, `simulationBySuggestion`, `mapAnalyze()`의 risk suggestion/soft check patch 변환

## Snapshot 규칙

`buildSnapshotForApi(project)`가 FE local model을 Backend `ProjectSnapshot`으로 변환합니다.

중요한 매핑 규칙은 아래와 같습니다.

- Backend로 보내는 일시는 `2026-05-08T18:00:00+09:00`처럼 서울 시간대 offset을 붙입니다.
- 멤버별 가능 시간이 없으면 `project.baseHours`가 `weekly_capacity_hours`로 들어갑니다.
- `pending` 마일스톤은 분석 요청에 보내지 않고, 승인/보관된 마일스톤만 보냅니다.
- FE 캘린더 이벤트는 Backend `calendar_events`로 변환됩니다.
- AI 추천 일정은 G2 승인 후 Backend가 반환한 `events_created`만 localStorage에 저장합니다.
- `/analyze` 응답의 `snapshot_hash`는 `/schedule:approve` 요청에 반드시 필요합니다.

Frontend에서 Backend가 상태를 저장한다고 가정하면 안 됩니다. 사용자가 분석 후 프로젝트 데이터를 수정했다면 `localProjectFingerprint` / `isProjectAnalysisStale`로 stale 여부를 확인하고, G2 승인 전에 분석을 다시 실행해야 합니다.

## 에러 처리

`apiClient.ts`의 `ApiError`, `userFacingApiError`, `taskInfoFieldsFromError`를 사용합니다.

| Code | FE 처리 |
|---|---|
| `task_info_insufficient` | 분석 또는 Task 분해 전에 부족한 Task 필드를 표시 |
| `circular_dependency` | `details.cycle_path`를 이용해 순환 의존 경로 표시 |
| `snapshot_hash_stale` | 일정 승인 전에 분석 재실행 |
| `rate_limited` | 잠시 후 재시도 안내 |
| `agent_failed` | 재시도 가능한 배너/메시지 표시 |
| `network_error` | 가능하면 마지막 분석 결과를 유지해서 표시 |

## Backend API가 바뀌었을 때

레포 루트에서 아래 명령을 실행합니다.

```bash
npm run generate:openapi
npm run check:openapi
```

요청/응답 필드가 바뀌었다면 `src/app/apiClient.ts`의 매핑도 함께 수정합니다. `src/app/generated/openapi.ts`는 직접 수정하지 않습니다.

API와 맞닿은 FE 변경 후 최소 검증은 아래입니다.

```bash
npm run test:fe
npm run build:fe
```

FE/BE 서버를 켠 상태에서 전체 로컬 인수인계 검증을 할 때는 아래를 실행합니다.

```bash
npm run check:local-servers
SMOKE_BASE_URL=http://127.0.0.1:8000 npm run smoke:local
E2E_FE_URL=http://127.0.0.1:5173/ E2E_BE_URL=http://127.0.0.1:8000 npm run test:e2e
```

## 빌드

```bash
npm run build
```

## E2E Smoke

```bash
E2E_FE_URL=http://127.0.0.1:5173/ \
E2E_BE_URL=http://127.0.0.1:8000 \
npm run test:e2e
```

Smoke test는 문서화된 5개 E2E 시나리오를 확인합니다: 정상 5개 Task 프로젝트, 수용 불가능한 capacity, 과부하 및 미배정 리스크, 순환 의존 에러, stale G2 일정 승인.

브라우저 실행 없이 Playwright 파일이 정상적으로 인식되는지만 확인하려면 아래 명령을 사용합니다.

```bash
npm run check:e2e-list
```
