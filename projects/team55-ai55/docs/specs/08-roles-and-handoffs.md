# 08. 역할 분담 및 협업 인터페이스

> 5인 팀 (AI Agent 개발 3명, Backend 1명, Frontend 1명) 의 책임 경계, 인계 지점, 일정.
> 원본 기획서 참여자: **이준형, 강인화, 박민우, 손의현, 이성은**.
> 5개 단일 책임 모듈로 1:1 배정 (역할 매핑은 팀 협의).

## 1. 역할 매트릭스

| 역할 | 인원 | 주 책임 | 단일 책임 모듈 | 명시적 비-책임 |
|---|---|---|---|---|
| **AI/Priority Agent** | 1 | 미배정 active Task 담당자 배정 + 결정적 우선순위 점수 + Task 분해 + Narrator | `backend/app/agents/priority/`, `backend/app/scoring/priority.py` | 슬롯 배치, 리스크 체크, 기존 담당자 재배정 |
| **AI/Schedule Agent** | 1 | DAG + 슬롯 패킹 + 충돌 검사 | `backend/app/agents/schedule/`, `backend/app/scoring/slot_packing.py` | LLM 호출, 점수 계산 |
| **AI/Risk Agent** | 1 | binary checks + 과부하 + Narrator | `backend/app/agents/risk/`, `backend/app/scoring/risk_checks/` | Task 분해, 슬롯 배치 |
| **Backend** | 1 | API Gateway / 오케스트레이션 / G2 게이트 / 캐시 | `backend/app/api/`, `backend/app/services/` | Agent 내부 로직 |
| **Frontend** | 1 | UI / localStorage / G1·G2·G3 인터랙션 | `frontend/` | 점수 계산, Agent 직접 호출 |

## 2. 인계(Handoff) 지점

```
[Frontend]
   │ POST /v1/projects (생성)
   │ POST /v1/projects/{id}/milestones:suggest
   │ POST /v1/projects/{id}/milestones:approve  [G1]
   │ POST /v1/projects/{id}/analyze       (snapshot)
   ▼
[Backend: super-graph]
   │ ProjectSnapshot (07 §2.6)
   ▼
[Priority Agent]  ──────────►  PriorityResponse (07 §3)
   │
   ├──parallel─────┐
   ▼               ▼
[Schedule Agent]   [Risk Agent]
   │               │
   ▼               ▼
ScheduleResponse  RiskResponse
   │               │
   └──────join─────┘
                   │
                   ▼
[Backend: pack → AnalyzeResponse]
   │
   ▼
[Frontend: 분석 패널 3 탭]
   │
   │ POST /v1/projects/{id}/schedule:approve [G2]
   │ POST /v1/projects/{id}/risk:simulate
   ▼
[Backend: G2 게이트 → events_created]
   │
   ▼
[Frontend: localStorage 캘린더 INSERT]
```

각 화살표는 **schema가 명시된 경계**다. schema 변경은 양쪽 담당자의 동의가 필요하다.

## 3. 핵심 협업 규칙

### 3.1 Schema-First
- 모든 인터페이스는 `07-data-contracts.md` 의 schema가 먼저 머지된 후 구현 시작.
- 구현 전 schema PR을 5명 모두 approve.
- Backend는 Pydantic v2, Frontend는 Zod로 schema에서 **자동 생성** (수기 동기화 금지).

### 3.2 Mock-First 개발
1주차에 모든 담당자는 자신의 입력/출력에 대한 **mock 응답 fixture**를 먼저 작성한다. 이로써 5명이 동시 병렬로 작업 가능.

| 담당자 | 1주차 mock 위치 |
|---|---|
| Priority | `backend/tests/fixtures/priority/expected.json` |
| Schedule | `backend/tests/fixtures/schedule/expected.json` |
| Risk | `backend/tests/fixtures/risk/expected.json` |
| Backend | mock subgraph로 Frontend에 응답 |
| Frontend | MSW(Mock Service Worker)로 Backend mock |

### 3.3 코드 소유권 (CODEOWNERS)
```
backend/app/agents/priority/        @priority-owner
backend/app/agents/schedule/        @schedule-owner
backend/app/agents/risk/            @risk-owner
backend/app/scoring/priority.py     @priority-owner
backend/app/scoring/slot_packing.py @schedule-owner
backend/app/scoring/risk_checks/    @risk-owner
backend/app/api/                    @backend-owner
backend/app/services/               @backend-owner
frontend/                           @frontend-owner
docs/specs/07-data-contracts.md     @priority-owner @schedule-owner @risk-owner @backend-owner @frontend-owner
```

`07-data-contracts.md` 변경은 5인 전원 승인 필요.

### 3.4 PR 사이즈
- 1 PR 당 ≤ 400 LOC
- 영역 횡단 PR 금지. 단, 체크 추가 / factors 추가는 예외 (3.5 참조).

### 3.5 체크 항목 / factors / 가중치 변경 (Cross-cutting)

체크리스트 또는 priority 5요소 변경 시 단일 PR에 다음이 모두 포함되어야 한다:
- 해당 spec 문서(`02-` 또는 `04-`)의 표 업데이트
- `backend/app/scoring/{priority|risk_checks}/` 새 클래스 또는 가중치 변경
- 단위 테스트 ≥ 4 케이스 (pass / fail / N/A / 경계값)
- `07-data-contracts.md`의 schema 영향 검토 (단순 추가는 schema 변경 없음)
- 새 체크의 `label` (한글) — 서버에서 직접 제공
- 골든 시나리오 5개 회귀 검증
- (factors 추가 시) Frontend `FactorsBar` 컴포넌트 업데이트

리뷰어: 해당 agent owner + backend-owner. (Frontend는 보통 코드 변경 불필요, factors는 예외.)

### 3.6 G1 / G2 / G3 승인 게이트 (전역 규칙)

| 게이트 | 정의 | 위반 시 |
|---|---|---|
| G1 | AI 마일스톤 제안은 PM 명시 승인 후에만 `Milestone.status="approved"` | Backend가 422 |
| G2 | 캘린더 INSERT는 PM 명시 승인 후에만 `InternalCalendarEvent.approved=true` | Backend G2 게이트 (snapshot_hash 체크 + 인덱스 검증 + override 충돌 검사) |
| G3 | Task의 importance/deadline/estimated_hours 변경과 기존 담당자 변경은 PM이 폼에서 직접 입력. 단, Priority Agent는 담당자 없는 `todo` / `in_progress` Task만 역할 단서 + 부하 기준으로 자동 배정 가능 | Frontend 강제 (suggestion → 폼 미리채움 → PM 확인 → 저장), Priority 자동 배정은 `task_assignments`로 추적 |

이 3개 게이트는 **테스트로 강제**된다. 위반은 P0 버그.

## 4. 정량성/주관성 가드레일 (전 역할 공통)

본 프로젝트의 **명시적 금지 영역**은 다음과 같이 다층 방어한다.

| 레이어 | 방어 수단 |
|---|---|
| Priority LLM 분해 프롬프트 | "Do not infer importance, deadline, assignee" |
| Risk Narrator 프롬프트 | "Use only provided facts and numbers. Forbidden: 매력, 호감, 인상, 게으, 느려, 무능…" |
| Priority Narrator 프롬프트 | 동일 금지 단어 + facts에 없는 숫자 인용 금지 |
| Backend 후처리 | 금지 단어 정규식 매칭 → 위반 시 1회 재시도 → fallback |
| Backend 로깅 | LLM 출력에 금지 단어 검출 시 `policy_violation` 메트릭 +1 |
| Frontend 표시 | 서버에서 받은 텍스트만 표시, 자체 추론 금지 |
| 테스트 | 금지 단어 회귀 테스트 (CI gating) |

### 4.1 금지 단어 리스트 (한국어)
```
매력, 매력적, 호감, 호감도,
인상, 성격, 신뢰감,
잘생, 예쁘, 멋지, 세련, 촌스러,
게으, 느려, 의지, 무능, 책임감, 능력,
나이, 연령, 성별,
직업이 ~처럼 보이는
```

### 4.2 허용 표현 (참고)
- 점수 인용 ("우선순위 87점")
- 사실 인용 ("마감까지 1.5일", "동시 진행 4건")
- 행동 권장 ("민우 → 인화 reassign")
- 범위 비교 ("기대 범위 70~95 대비 현재 65")

## 5. 마일스톤 통합 보기 (3주)

원본 기획서 §5의 6단계 로드맵을 3주에 압축.

| 주차 | Priority | Schedule | Risk | Backend | Frontend |
|---|---|---|---|---|---|
| **1주** | LangGraph sub-graph 골격 + 담당자 자동 배정 + 결정적 함수 5종 + DAG validator + 골든 8케이스 | sub-graph 골격 + topo_sort + working_windows + task_blocks | sub-graph 골격 + Group A,B 9개 체크 + task_risk_level 룰 | LangGraph 셋업 + super-graph 골격(stub sub-graph) + FastAPI 스캐폴드 + projects/milestones:suggest | 라우팅 + Setup 위저드 + Task CRUD + localStorage adapter |
| **2주** | LLM 분해 노드 + verify_decomposition + 분기 함수 | find_candidate_slots + compute_fit_score + detect_conflicts + 결정적 골든 5케이스 | Group C,D 7개 체크 + member_workload + fix_template + dedup | analyze 라우터 + 실제 sub-graph 연결 + snapshot_hash + 캐시 | 분석 패널 3 탭 + 캘린더 그리드 + G1·G2 승인 흐름 |
| **3주** | Narrator + safety_filter + 룰 fallback + 담당자 보존/배정 결정성 회귀 | LLM Reranker + verify_rerank + skip 분기 + safety 회귀 | Soft Checks (S1~S5) + verify_soft_checks + Narrator + safety_filter + simulate endpoint 공유 | schedule:approve G2 게이트 + risk:simulate(hard lane) + 관측성 + E2E + LLM 호출 카운터 메타 | rerank_rationale/source 표시 + soft_checks AI 직관 영역 + 시뮬레이션 + export/import + 접근성 + Playwright + 발표 폴리싱 |

각 주 종료 시점 **인테그레이션 데이**: 금요일 오후, 5인 모두 코드 머지 후 e2e 시나리오 1회 통과.

### 5.1 LangGraph 공통 규칙 (전 Agent + Backend)
- 각 Agent는 자신의 sub-graph를 `compile()` 결과로 export. 모듈 경로: `app.agents.{name}.{name}_subgraph`
- State 모델은 Pydantic v2. 변경 시 sub-graph 담당자 + Backend 담당자 동시 리뷰.
- 노드는 **단일 책임** (한 가지 도구 OR 한 가지 LLM 호출). 노드 함수 시그니처: `(state) -> dict[str, Any]` (부분 업데이트 반환).
- 분기 함수는 결정적. State의 결정적 필드만 참조.
- 노드 이름은 snake_case 동사구 (예: `compute_priority`, `pack_tasks`, `evaluate_checks`).
- 모든 sub-graph는 단위 테스트로 4개 시나리오 이상 통과해야 한다 (정상 / 분기 일부 / 분기 전부 / 실패).
- Backend의 super-graph는 Agent sub-graph의 **State schema 변경에 자동으로 영향받지 않는다** — sub-graph가 출력하는 최종 필드(PriorityResponse / ScheduleResponse / RiskResponse)만 보면 된다.
- LangSmith는 환경변수로 활성화 (`LANGCHAIN_TRACING_V2=true`).

## 6. 의사결정 로그 (DACI)

| 결정 항목 | Driver | Approver | Contributors | Informed |
|---|---|---|---|---|
| 새 RiskCheck 추가 | risk-owner | risk + backend | priority/schedule | frontend |
| Priority factors 가중치 변경 | priority-owner | priority + backend | risk | frontend |
| 새 enum 값 (importance, action 등) | 발의자 | 5인 전원 | - | - |
| LLM 모델 교체 (Upstage 외) | priority/risk owner | 해당 owner | backend (비용/속도) | 전원 |
| Frontend 큰 UI 변경 | frontend-owner | frontend + 발표 담당 | - | 전원 |
| Google Calendar 연동 추가 (post-MVP) | 발의자 | 5인 전원 + 사전 시연 | - | - |

## 7. 통합 테스트 시나리오 (E2E 5개)

3주차 발표 전 모두 통과 필수.

| # | 시나리오 | 의도 | 기대 결과 |
|---|---|---|---|
| 1 | 정상 프로젝트 (5 Task, 2 멤버, 빈 캘린더) | 행복 경로 | 모든 Task가 priority + schedule + risk 모두 정상, blockers_failed=[] |
| 2 | 마감 1일 전 8h Task + 4h 캘린더 점유 | unschedulable 검출 | schedule.unschedulable에 `no_capacity_before_deadline` 사유 |
| 3 | 한 명에게 6 Task 집중 | 담당자 업무 쏠림 검출 | `workload_concentration` fail + reassign 제안 |
| 4 | 순환 의존 입력 (A → B → A) | DAG 위반 | Risk `dependency_correctness` fail + `remove_predecessor` 제안 |
| 5 | snapshot 변경 후 G2 승인 시도 | stale hash 감지 | 409 snapshot_hash_stale + 자동 재분석 → 새 슬롯으로 재승인 흐름 |

각 시나리오는 골든 snapshot + 기대 응답 fixture로 저장 (`backend/tests/fixtures/e2e/`).

## 8. 발표 자료 책임

| 항목 | 담당 |
|---|---|
| 슬라이드 (배경/문제/접근법) | 1인 (팀 협의) |
| 데모 시연 | Frontend 담당 |
| 아키텍처/Agent 흐름 설명 | Backend 담당 |
| 우선순위 5요소 정량 평가 | Priority 담당 |
| 슬롯 패킹 알고리즘 / 결정성 강조 | Schedule 담당 |
| 16개 체크 + 과부하 검출 | Risk 담당 |

## 9. 리스크 및 컨틴전시

| 리스크 | 컨틴전시 |
|---|---|
| Upstage API 한도 초과 | LLM 분해/Narrator는 fallback 룰로 대체. 결정적 산출물(점수/슬롯/체크)만으로도 동작. |
| LLM이 schema 위반 빈발 | 재시도 1회 + fallback. CI에서 schema_pass_rate 모니터링. |
| 슬롯 패킹이 너무 보수적 (모두 unschedulable) | 골든 셋 검증, working_hours/estimated_hours 입력 가이드 강화. |
| 점수 분포 이상 (모두 80+) | priority-owner: 가중치 재조정, 골든 셋 재라벨. |
| localStorage 데이터 손실 | export/import 강조, 발표 시 export 파일을 별도로 백업. |
| 발표 시연 실패 | 사전 녹화한 데모 영상 fallback 준비. |
| 외부 캘린더 연동 요구 사용자 피드백 | "MVP 제외 — 원본 기획서 명시" 답변 + post-MVP 로드맵 슬라이드. |

## 10. 정의된 "완료(Done)" 기준

다음을 모두 만족해야 프로젝트 완료로 본다.

- [ ] 16개 RiskCheck + 5개 Priority factor 모두 단위 테스트 통과
- [ ] G2 게이트 단위 테스트 통과 (stale hash, out_of_range, override conflict, 정상 4 케이스)
- [ ] 5개 E2E 시나리오 통과
- [ ] Schema Pass Rate ≥ 98% (자동 측정)
- [ ] 동일 snapshot 5회 호출 시 priority_scores + slot_proposals(결정적 부분) + hard checks 100% 동일
- [ ] LLM Reranker safety: verify_rerank 위반 시 100% deterministic fallback (E2E로 검증)
- [ ] Soft Checks safety: 환각 task_id / confidence < 0.5 / 금지 단어는 100% verify로 차단
- [ ] 금지 단어 회귀 테스트 통과 (위반 0건)
- [ ] Latency P95 (analyze) ≤ 7s, (cache hit) ≤ 100ms, (risk:simulate hard lane) ≤ 300ms
- [ ] localStorage export/import 동작 (3MB 이하 페이로드)
- [ ] 발표 데모 1회 무사고 시연

## 11. 향후 (Post-MVP) 후보

본 spec은 MVP에 한정. 다음은 발표 후 별도 마일스톤 후보:

- Google Calendar 양방향 동기화 (OAuth)
- 다중 PM / 팀원 초대 / 권한
- Slack 알림 (마감 임박 / 과부하)
- 모바일 PWA
- 학습 기반 estimated_hours 보정 (과거 실측 기반)
- 대시보드 (멀티 프로젝트 합산 부하 차트)
