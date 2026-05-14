# 06. Frontend — 사양

> 담당자: Frontend 개발자 1명
> 책임: 사용자 입력 수집 / Agent 추천 시각화 / 승인 인터랙션 / 내부 캘린더 / localStorage 영속화

## 1. 책임

1. 프로젝트/팀원/근무가능시간 입력 폼 + Task CRUD 폼
2. 마일스톤 / 우선순위 / 슬롯 후보 / 리스크 시각화
3. **G1, G2, G3 승인 인터랙션** (마일스톤, 일정, 핵심 필드 변경)
4. 내부 캘린더 (Week/Day 그리드) 표시 + 드래그 시 Backend 재요청
5. localStorage 영속화 (서버에 영속 저장소 없음 — 본 MVP)
6. localStorage 데이터 export/import (사용자 데이터 안전성)

## 2. 비-책임 (명시적 금지)

| 항목 | 이유 |
|---|---|
| 클라이언트측 우선순위/충돌 재계산 | 서버 결정성 깨짐 |
| 사용자에 대한 주관적 평가 표시 | 본 프로젝트 명시적 금지 |
| 외부 캘린더 (Google Calendar) 호출 | MVP 제외 (원본 기획서 84,96행) |
| 직접 Upstage API 호출 | API 키 노출 — 항상 Backend 경유 |
| 자동 PM 승인 (사용자 클릭 없이 캘린더 INSERT) | G2 게이트 위반 |
| 서버에 PII 영속 저장 | 본 MVP는 서버 영속 없음 |

## 3. 기술 스택

원본 기획서 §4: `React 또는 Next.js`. 본 spec은 **Next.js 14 (App Router)** 권장 (이유: 라우팅 + i18n + SSR가 곧바로 작동, 빌드/배포 표준).

- TypeScript
- 상태관리: React Context + useReducer (단일 PM, 단순 흐름)
- 스타일: Tailwind CSS
- 폼: react-hook-form + zod
- API 클라이언트: 자동생성 (OpenAPI → typescript-fetch 또는 orval)
- 캘린더: react-big-calendar 또는 자체 구현 (week 그리드)
- 빌드: Next.js (Turbopack)
- 테스트: Vitest + React Testing Library + Playwright

## 4. 화면 구성

### 4.1 `/projects` — 프로젝트 목록
- 좌: localStorage의 프로젝트 카드 리스트 (이름, 기간, 진행률 합)
- 우: "+ 새 프로젝트" 버튼 → 모달 (이름/기간/목표 입력)
- 하단: localStorage export (JSON 다운로드) / import 버튼

### 4.2 `/projects/[id]/setup` — 초기 설정 (1회성)
원본 기획서 §3 사용자 시나리오 1~5에 대응.

#### 단계 (Wizard)
1. **팀원 추가** — name, role, weekly_capacity_hours, available_hours (요일별)
2. **근무가능시간 기본값** — weekday/weekend 시간 윈도우
3. **마일스톤 제안** — `POST /milestones:suggest` 호출 → 제안 리스트 표시
4. **마일스톤 승인 [G1]** — PM이 체크박스로 채택할 항목 선택, 이름/날짜 수정 가능, "승인" 버튼 → `POST /milestones:approve`

### 4.3 `/projects/[id]/tasks` — Task 보드
- 좌측 사이드: Task CRUD 폼 (모든 핵심 필드 + 의존성 선택 콤보)
- 중앙: Task 목록 (status별 칸반 또는 리스트 토글)
  - 각 카드: title, importance 배지, deadline, progress bar, assignee 아이콘
  - **task_risk_levels**의 색상으로 카드 좌측 stripe (overdue=빨강 / at_risk=주황 / watch=노랑 / ok=회색)
- 우측: AI 분석 패널 (다음 절)
- 상단 액션: "AI 분석 다시 실행" (snapshot_hash 변경 시 자동 + 수동)

### 4.4 AI 분석 패널 (Tasks 화면 우측)
`POST /analyze` 결과를 3개 탭으로 표시:

#### 탭 1: 우선순위 (Priority)
- rank 순 Top-10 Task 카드 리스트
- 각 카드:
  - rank, title, score
  - factors 차트 (5개 가로 막대: deadline / importance / predecessor / progress / overload)
  - rationale (LLM 설명)
- "Task 분해 요청" 버튼 (체크박스 다중 선택) → 다음 analyze 호출에 `request_decomposition_for` 포함
- 분해 결과(`task_decompositions`)는 카드 아래 펼침 영역 → "Task로 추가" 버튼 [G3 게이트] → 폼 미리채움 → PM 확인/저장

#### 탭 2: 일정안 (Schedule)
- Task별 후보 슬롯 카드 리스트
- 각 카드:
  - task title + 추천 슬롯 1개 (선택된 candidate_slots[selected_index])
  - quality 배지 색상 (preferred=초록 / acceptable=노랑 / fallback=주황)
  - fit_score, conflicts 표시
  - **rerank_rationale** (있을 때만, 작은 회색 텍스트로 "AI 추천 이유: ...")
  - **rerank_source** 배지 — `llm_reranked`이면 "AI 정렬", `deterministic`이면 표시 없음 (또는 작은 ⚙ 아이콘으로 fallback 표시)
  - "다른 슬롯 보기" 토글 → 나머지 후보들 (LLM이 재정렬한 순서)
  - 시간 변경 (datetime input) → override
  - 체크박스 (포함 여부)
- 하단: "선택한 일정 승인 [G2]" 버튼 → `POST /schedule:approve` → 응답의 events_created를 localStorage 캘린더에 INSERT
- unschedulable Task는 별도 영역, reason 라벨 + Risk 탭에서 fix 제안 보기 링크

#### 탭 3: 리스크 (Risk)
- 상단: blockers_failed 빨간 알림 + summary 박스
- 4개 그룹 헤더 + 체크 리스트:
  - ✓ pass: 회색
  - ✗ fail: 강조 + evidence_facts 펼치기
  - — N/A: 흐림
- task_risk_levels 분포 미니 차트 (몇 건 overdue 등)
- member_workload 막대 차트 (utilization, 1.0 초과는 빨강)
- **AI 직관 (Soft Checks) 영역** — hard checks와 시각적으로 분리된 별도 카드:
  - 헤더 라벨 "AI 직관 — PM 확인 필요" + ⓘ 툴팁 ("결정적 룰이 못 잡는 패턴입니다. PM의 판단이 필요합니다.")
  - 각 항목:
    - trigger_label 한글 매핑 + confidence (예: "암묵적 의존 의심 · 78% 확신")
    - involved_task_ids 칩 + supporting_facts 펼치기
    - user_facing_text
    - 액션: "확인하고 적용" (suggested_action을 G3 폼 미리채움) / "무시" (이 세션 동안 숨김)
  - 빈 배열일 때는 "AI 직관에서 발견된 추가 위험 없음" 작은 회색 텍스트
- suggestions 카드 리스트 (hard suggestions):
  - action 요약 (예: "민우 → 인화 reassign")
  - rationale_facts 인용
  - "시뮬레이션" 토글 → `POST /risk:simulate` → 변경된 체크 to_pass / to_fail 표시
  - "적용 [G3]" 버튼 → 해당 Task 폼 미리채움 → PM 확인 → 폼 저장 → analyze 재호출

### 4.5 `/projects/[id]/calendar` — 내부 캘린더
- Week 그리드 (월~일, 시간축 6~24시)
- 이벤트 카드: task title + assignee 색상
- 이벤트 클릭: Task 상세 + 시간 수정 (재분석 트리거 안 함, 단일 이동만 — 충돌은 빨간 테두리로 즉시 표시)
- 미승인 슬롯(approved=false)은 표시하지 않음 (G2 강제)
- "AI 일정 검토" 버튼 → 분석 패널 탭 2로 이동

### 4.6 `/projects/[id]/settings` — 설정
- 프로젝트 메타 수정
- 멤버 추가/삭제
- localStorage export / import / clear

## 5. 데이터 흐름

### 5.1 localStorage 스키마

```typescript
interface LocalStore {
  schemaVersion: 1;
  projects:        Project[];
  membersByProject:        Record<string, Member[]>;
  tasksByProject:          Record<string, Task[]>;
  milestonesByProject:     Record<string, Milestone[]>;
  calendarEventsByProject: Record<string, InternalCalendarEvent[]>;
  // 캐시 (선택)
  lastAnalyzeResponseByProject: Record<string, AnalyzeResponse>;
  lastSnapshotHashByProject:    Record<string, string>;
}
```

키: `omc-pm-55:v1` (schemaVersion 변경 시 마이그레이션 함수)

### 5.2 Analyze 결과의 Task 반영/저장

Frontend는 `POST /analyze` 성공 후 Priority 결과를 local Task 객체에 반영한다.

- `task_assignments[]`는 local Task의 `assigneeId`에 저장한다. 이 변경은 입력 시점에 `assigneeId=null`이고 `status in ("todo", "in_progress")`였던 Task에만 실제 Task 변경으로 인정된다.
- 이미 PM이 지정한 `assigneeId`는 Priority 결과로 덮어쓰지 않는다. `blocked`, `review`, `done`, `cancelled` Task도 Priority 자동 배정 대상이 아니다.
- `tasks_priority[]`는 각 Task에 derived analysis fields로 저장하거나 표시용 projection으로 병합한다. local Task 필드는 camelCase로 `priorityScore`, `priorityRank`, `priorityFactors`, `priorityEvidenceFacts`, `priorityRationale`, `priorityUpdatedAt`을 사용한다.
- derived analysis fields는 PM-owned fields가 아니므로 폼에서 직접 편집하지 않는다. `title`, `description`, `importance`, `dueDate`, `estimatedHours`, `progress`, `status`, `predecessorIds` 같은 PM-owned fields는 analyze 결과로 변경하지 않는다.
- snapshot builder와 stale fingerprint는 derived analysis fields를 제외해야 한다. Priority 점수/rank/evidence/rationale 갱신만으로 `snapshot_hash_stale`이나 자동 재분석을 유발하면 안 된다.

### 5.3 데이터 플로우 (한 사이클)

```
[Upload form 입력]
   │ 사용자가 Task 추가/수정
   ▼
[localStorage 저장]
   │
   ▼
[snapshot 빌드 (현재 상태 직렬화)]
   │
   ▼
POST /v1/projects/{id}/analyze
   │ 200
   ▼
[task_assignments/tasks_priority를 local Task에 병합 + lastAnalyzeResponse 저장 + 화면 갱신]
   │
   ├── 우선순위 탭 → 분해 요청 → 새 analyze
   ├── 일정 탭 → 슬롯 선택 → POST /schedule:approve [G2]
   │     │ 200
   │     ▼ events_created → localStorage.calendarEvents에 INSERT
   │
   └── 리스크 탭 → suggestion 적용 → 폼 미리채움 → PM 확인 → 저장 [G3]
                                                              │
                                                              ▼
                                                    [snapshot 변경 → 자동 재분석]
```

### 5.4 stale-while-revalidate

마지막 analyze 응답을 즉시 표시하되 snapshot_hash가 다르면 재분석을 백그라운드로 호출. 응답 도착 시 부드럽게 갱신.
단, `tasks_priority`에서 온 derived analysis fields만 바뀐 경우에는 snapshot_hash 변경으로 보지 않는다.

## 6. 표시 규칙 (정량성/주관성 금지)

### 6.1 허용
- 점수 그대로 표시 ("우선순위 87/100")
- factors 막대 ("마감 0.85 / 중요도 0.75 / 선행 1.0 / 진척 0.4 / 부하 0.2")
- 사실 인용 ("마감까지 1.5일", "동시 진행 4건")
- 행동 권장 ("민우 → 인화 reassign")

### 6.2 금지 표시
- "이 PM은 일을 잘하시네요" 류 평가
- "민우님이 게으른 것 같아요" 류 인격 추정
- 점수 변동을 별/이모지/하트로 의미 부여
- 서버에서 안 준 추가 추론
- 외부 캘린더 통합 흉내

### 6.3 그룹 한글 매핑
| 서버 키 | 표시 라벨 |
|---|---|
| deadline | 마감 |
| dependency | 선후행 |
| workload | 담당자 부하 |

### 6.4 risk_level 색상
| 서버 값 | 색상 | 라벨 |
|---|---|---|
| ok | 회색 | "정상" |
| watch | 노랑 | "관찰" |
| at_risk | 주황 | "주의" |
| overdue | 빨강 | "지연" |

### 6.5 importance 표시 (PM이 입력한 값 그대로)
| enum | 라벨 | 배지 색 |
|---|---|---|
| low | 낮음 | 회색 |
| medium | 보통 | 파랑 |
| high | 높음 | 보라 |
| critical | 중요 | 빨강 |

### 6.6 soft_check trigger_label 한글 매핑
| 서버 값 | 표시 라벨 |
|---|---|
| implicit_dependency_suspected | "암묵적 의존 의심" |
| repeated_delay_root_cause | "반복 지연 원인" |
| milestone_task_mismatch | "마일스톤-Task 정렬 불일치" |
| task_definition_too_vague | "Task 정의 모호" |
| duplicate_task_suspected | "중복 Task 의심" |

### 6.7 rerank_source 배지
| 서버 값 | 표시 |
|---|---|
| llm_reranked | 작은 "AI 정렬" 배지 + 옆에 rerank_rationale |
| deterministic | 표시 없음 (또는 fallback 발생 시 ⚙ 아이콘 + 툴팁 "기본 정렬 사용") |

## 7. 컴포넌트 구조

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── projects/page.tsx
│   │   ├── projects/[id]/setup/page.tsx
│   │   ├── projects/[id]/tasks/page.tsx
│   │   ├── projects/[id]/calendar/page.tsx
│   │   └── projects/[id]/settings/page.tsx
│   ├── components/
│   │   ├── TaskCard.tsx
│   │   ├── TaskForm.tsx
│   │   ├── PriorityPanel.tsx
│   │   ├── SchedulePanel.tsx
│   │   ├── RiskPanel.tsx
│   │   ├── FactorsBar.tsx        # 5개 막대
│   │   ├── WorkloadChart.tsx
│   │   ├── CalendarGrid.tsx
│   │   ├── SuggestionCard.tsx
│   │   └── ApprovalBar.tsx       # G1/G2 공통 승인 액션 바
│   ├── api/
│   │   ├── client.ts             # 자동생성 OpenAPI client
│   │   └── schemas.ts            # zod (07-data-contracts와 동기)
│   ├── hooks/
│   │   ├── useAnalyze.ts
│   │   ├── useApproveSchedule.ts
│   │   └── useRiskSimulate.ts
│   ├── store/
│   │   ├── localStore.ts         # localStorage adapter (versioning + migration)
│   │   ├── snapshot.ts           # build snapshot from store
│   │   └── exportImport.ts
│   ├── lib/
│   │   ├── format.ts             # 점수/시간 포맷
│   │   ├── colors.ts             # quality/risk 색상
│   │   └── i18n.ts               # 그룹/라벨 매핑
│   └── styles/
└── package.json
```

## 8. 에러 처리 (사용자 메시지)

| 서버 코드 | UI 처리 |
|---|---|
| 400 / 422 task_info_insufficient | 폼 필드별 빨간 메시지 + 입력 보완 안내 (기획서 §4 매칭) |
| Risk dependency_correctness fail | 리스크 탭: 순환 경로/마감 역전/일정 역전 근거 + PM 조치 제안 표시 |
| 409 snapshot_hash_stale | toast: "데이터가 변경되어 분석을 다시 실행합니다" → 자동 재분석 |
| 429 rate_limited | toast: "잠시 후 다시 시도해 주세요" |
| 502 agent_failed | banner: "AI 분석 일부가 실패했습니다. 다시 시도해 주세요" + 재시도 버튼 |
| 네트워크 오류 | offline 배너 + "마지막 분석 결과 표시 중" |

## 9. 접근성 (a11y)

- 차트는 색상만으로 정보 전달하지 않음 (텍스트 라벨 + aria-label)
- 캘린더 그리드 키보드 탐색 (방향키)
- 모든 인터랙티브 요소 focus visible
- 빨강/초록 동시 표시 시 형태 차이 (테두리 굵기, 아이콘) 추가
- Tab 순서: Header → Tab 선택 → Tab 내부

## 10. 성능 목표

| 지표 | 목표 |
|---|---|
| 첫 페이지 로드 (FCP) | ≤ 1.5s (3G fast) |
| Task 입력 → snapshot 저장 | ≤ 50ms |
| analyze 호출 → UI 갱신 | ≤ 5.5s (서버 5s + 렌더 0.5s) |
| 캘린더 렌더 (50 events) | ≤ 100ms |
| 번들 크기 (gzip) | ≤ 300KB |

## 11. 테스트 전략

### 11.1 단위
- localStore: 마이그레이션 / export / import / 손상 데이터 복원
- snapshot 빌더: 누락 필드 정규화
- format / colors / i18n

### 11.2 컴포넌트
- FactorsBar: 5개 막대 비율
- SuggestionCard: 시뮬레이션 토글 동작
- TaskForm: importance/deadline/predecessor 검증
- ApprovalBar: 체크박스 다중 선택 → G2 호출 페이로드

### 11.3 E2E (Playwright)
- 시나리오 1: 신규 프로젝트 → 팀원 추가 → 마일스톤 제안 → 승인 → Task 5개 입력 → 분석 → 일정 승인 → 캘린더 표시
- 시나리오 2: snapshot 변경 후 stale 응답 처리
- 시나리오 3: 순환 의존 입력 → Risk `dependency_correctness` blocker → 사용자 수정 또는 시뮬레이션 → 재분석
- 시나리오 4: 담당자 과부하 → reassign 적용 [G3] → 재분석 → 부하 감소

## 12. 마일스톤

| 주차 | 산출물 |
|---|---|
| 1주차 | 라우팅 + Setup 위저드 + Task CRUD 폼 + localStorage adapter |
| 2주차 | 분석 패널 3 탭 + 캘린더 그리드 + G1/G2 승인 흐름 |
| 3주차 | 시뮬레이션 + export/import + 접근성 + Playwright 5 시나리오 + 발표 폴리싱 |

## 13. 다른 역할과의 인터페이스

- **Backend**: OpenAPI schema(`/openapi.json`)를 single source of truth로 받음. CI에서 schema diff 시 자동 PR 생성.
- **Agent 담당자들**: 새 RiskCheck 추가 시 label은 서버에서 한글로 직접 옴 → Frontend는 i18n 매핑 없이 표시. `factors` 필드 추가 시 FactorsBar 컴포넌트 업데이트 (cross-cutting PR — `08-roles-and-handoffs.md §3.5`).
- **PM (사용자)**: 데이터는 브라우저 localStorage에만 → 사용자가 명시적으로 export 받지 않으면 데이터 사라짐 → 설정 화면에서 강한 경고 + 정기 export 권장 메시지.

## 14. 정직성 노트

- 본 Frontend는 **두꺼운 PM 도구**가 아니다. 캡스톤 발표용 MVP에 맞게 5개 화면으로 축소.
- 캘린더는 react-big-calendar 같은 라이브러리로 충분 — 일정 직접 편집은 본 MVP의 핵심이 아니다 (Agent 추천 → 승인이 핵심).
- "외부 캘린더 연동 안 되네요"라는 사용자 피드백은 **MVP 의도**로 답한다. PDF 84,96행에 명시된 결정.
- localStorage는 single-browser 한계가 있다 — 데모 시 같은 브라우저에서 시연하고, export 파일을 발표자료에 첨부.
