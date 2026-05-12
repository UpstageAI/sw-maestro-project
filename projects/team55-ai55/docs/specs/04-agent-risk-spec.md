# 04. Risk Agent — 사양

> 담당자: AI 개발 #3
> 책임: ProjectSnapshot + PriorityResponse (+ ScheduleResponse) → **결정적 binary checks + LLM Soft Checks + 담당자 부하 + 설명 가능한 fix 제안**
> **Architecture**: Pass/Fail 결정적 checks + Critical Blocker + **LLM Soft Checks (텍스트 기반 추론)** + Failed-check 1:1 제안 + LLM Narrator

## 1. 책임

1. 14개 binary 체크 항목을 `마감 / 선후행 / 담당자 부하` 3개 그룹으로 결정적으로 평가 (pass / fail / not_applicable)
2. Task별 risk_level 산출 (ok/watch/at_risk/overdue)
3. 담당자별 주간 부하 계산 (utilization, overloaded 판정)
4. Critical blocker 위반 시 강조 표시
5. 각 failed check에 대한 1:1 fix action 생성 (action 어휘 7종)
6. **LLM Soft Checks**: Task title/description/delay_reason 등 텍스트에서 결정적 룰이 못 잡는 패턴 추론 (예: 암묵적 의존, 반복 지연 사유, 마일스톤-Task 불일치). confidence + supporting_facts 동반.
7. LLM Narrator가 프로젝트 전체 리스크 요약 (≤400자, facts만 인용)

원본 기획서 §1 4가지 핵심 문제 중 #4 "마감 리스크와 담당자 과부하를 사전에 파악하기 어려운 문제"를 본 Agent가 정면으로 다룬다.

## 2. 비-책임 (명시적 금지)

| 금지 항목 | 이유 |
|---|---|
| Risk를 LLM이 자유 추정 | 본 spec은 binary check로 일원화 |
| 담당자 인격/태도 평가 | 윤리 위험, 본 프로젝트 명시적 금지 |
| 캘린더 자동 재배치 | Schedule Agent의 reschedule 제안만, 실행은 G2 |
| Task 자동 분해/재할당 | Priority/Schedule 제안만, 실행은 PM |
| 외부 데이터(Slack 활동량, 깃허브 커밋 등) 참조 | MVP 범위 외 |
| "이 PM이 일을 못한다" 같은 평가 | 명시적 금지 |

## 3. 입력
```python
class RiskRequest(BaseModel):
    snapshot: ProjectSnapshot
    priority: PriorityResponse
    schedule: Optional[ScheduleResponse] = None  # 일부 체크는 schedule 필요
    now: datetime
```

## 4. 출력

`07-data-contracts.md §5` RiskResponse schema 100% 준수.

## 5. 체크 항목 정의 (총 3개, 3 그룹)

> **모든 체크는 결정적 함수 (`backend/app/scoring/risk_checks/`)와 1:1 대응**한다.

### 마감 — 1 check
| ID | 라벨 | Pass 조건 | Blocker |
|---|---|---|---|
| deadline_feasibility | 마감일까지 완료 가능성 | 마감 지난 active task 0건, `no_capacity_before_deadline` 0건, 남은 estimated_hours ≤ 남은 일수×8h | **yes** |

### 선후행 — 1 check
| ID | 라벨 | Pass 조건 | Blocker |
|---|---|---|---|
| dependency_correctness | 선후행 관계 오류 | DAG 순환 0건, 선행 task 마감 ≤ 후행 task 마감, 후행 slot 시작 ≥ 선행 slot 종료 | **yes** |

### 담당자 부하 — 1 check
| ID | 라벨 | Pass 조건 | Blocker |
|---|---|---|---|
| workload_concentration | 담당자 업무 쏠림 | 모든 member utilization ≤ 1.0, utilization 표준편차 ≤ 0.4, 최대 담당자 배정 비중 < 0.85 | no |

### 5.1 N/A 처리
- workload_concentration은 schedule이 없으면 N/A
- N/A 체크는 분모/분자 모두에서 제외

### 5.2 task_risk_level 산출 (결정적 룰)

```python
def task_risk_level(task, priority_score, now):
    if task.deadline and task.deadline < now and task.status not in ("done", "cancelled"):
        return "overdue"
    if priority_score >= 80 and task.progress_percent < 30:
        return "at_risk"
    if priority_score >= 60:
        return "watch"
    return "ok"
```

### 5.3 member_workload 산출

```python
def member_workload(member, snapshot, schedule, now):
    horizon_end = now + timedelta(days=7)
    scheduled = sum(
        slot_hours(s) for proposal in schedule.slot_proposals
        for s in [proposal.candidate_slots[proposal.selected_index]]
        if s.member_id == member.member_id and s.starts_at < horizon_end
    )
    capacity = (member.weekly_capacity_hours or 40)
    utilization = scheduled / capacity if capacity > 0 else 0
    return {
        "member_id": member.member_id,
        "scheduled_hours_next_7d": scheduled,
        "capacity_hours": capacity,
        "utilization": round(utilization, 2),
        "is_overloaded": utilization > 1.0,
    }
```

## 6. 점수 / 등급 산출

본 Agent는 **종합 점수를 산출하지 않는다.** 대신:
- `blockers_failed`: blocker 체크 fail의 ID 목록 → UI에서 빨간 배지
- `task_risk_levels`: Task별 색상
- `member_workload`: 담당자별 막대
- `soft_checks`: LLM 추론 위험 (별도 섹션, hard check와 분리 표시)

이 4가지 출력으로 PM이 한눈에 위험을 파악한다 — 종합 점수가 없어 평균 효과로 위험이 묻히지 않는다.

## 6A. LLM Soft Checks (텍스트 기반 추론)

### 6A.1 의도

결정적 16 체크는 숫자(deadline, progress, utilization)만 본다. 하지만 PM이 진짜 걱정하는 패턴은 텍스트에 숨어 있다:

- **암묵적 의존성**: Task A "로그인 API 구현"과 Task B "회원가입 페이지" 사이에 predecessor가 없지만, 실제로는 A가 B의 선행이어야 한다.
- **반복 지연 사유**: 여러 Task의 `delay_reason`이 모두 "외부 API 응답 대기" → 프로젝트 차원의 외부 의존 리스크.
- **마일스톤-Task 정렬 불일치**: 마일스톤 "MVP 출시"인데 Task 제목이 모두 "리팩토링", "문서 정리" → 출시 본래 작업 누락 의심.
- **모호한 정의**: Task title이 "기능 개선" 같은 한 단어 → estimated_hours 신뢰도 낮음.
- **중복 의심**: 두 Task의 title/description이 의미상 같음 → 한쪽 통합 권장.

이런 패턴은 결정적 룰로 잡기 어렵고, **LLM의 자연어 추론이 가장 가치를 내는 영역**이다.

### 6A.2 Soft Check 카탈로그 (초기 5종)

| ID | 라벨 | 트리거 (LLM이 찾는 패턴) | suggested action |
|---|---|---|---|
| S1 | implicit_dependency_suspected | 두 Task의 title/description이 "X 구현" → "X 사용" 관계로 보임 + predecessor 없음 | `add_predecessor` |
| S2 | repeated_delay_root_cause | ≥ 2개 Task의 delay_reason이 의미적으로 동일 카테고리 | (정보성, action 없음) |
| S3 | milestone_task_mismatch | 마일스톤 이름의 의도와 그 마일스톤 Task 제목들의 분포가 어긋남 | (정보성) |
| S4 | task_definition_too_vague | Task title이 단어 1~2개 + description 짧음 + estimated_hours 낮은 confidence | (PM에게 description 보강 요청) |
| S5 | duplicate_task_suspected | 두 Task가 의미상 동일 작업으로 보임 | `split_task` 또는 통합 권장 (정보성) |

ID는 `S` 접두 (Soft). 이후 추가는 PR 합의.

### 6A.3 LLM 호출 형태

| 항목 | 값 |
|---|---|
| 호출 횟수 | 1회 (배치, 모든 Task + delay_reason + 마일스톤을 한 번에) |
| 모델 | Upstage Solar |
| temperature | 0.2 (결정적 hard check와 달리 약간의 창의성 허용. 단 schema 강제) |
| timeout | 4s. 초과 시 soft_checks=[] 빈 배열 + warning |

### 6A.4 출력 schema

각 soft_check 결과는 다음 구조:
```json
{
  "id": "S1",
  "trigger_label": "implicit_dependency_suspected",
  "confidence": 0.78,
  "involved_task_ids": ["task_xxx", "task_yyy"],
  "supporting_facts": [
    "task_xxx.title='로그인 API 구현'",
    "task_yyy.title='회원가입 페이지' description references '로그인 토큰'",
    "predecessor_ids 비어있음"
  ],
  "suggested_action": {
    "type": "add_predecessor",
    "target_task_id": "task_yyy",
    "from": "(없음)",
    "to": "task_xxx"
  },
  "user_facing_text": "회원가입 페이지가 로그인 API 토큰을 사용하지만 선행 관계가 없습니다."
}
```

`07-data-contracts.md` RiskResponse에 `soft_checks` 배열 필드로 추가됨 (별도 PR로 schema 갱신).

### 6A.5 안전 제약

- **soft_check는 절대 hard check를 덮어쓰지 않는다.** UI에 별도 영역으로 표시.
- **risk_level / blockers_failed에 영향 없음.** soft_check만으로 task_risk_level이 변하지 않음 (PM이 confirm 후 hard 데이터 수정 시에만 영향).
- **confidence < 0.5 결과는 폐기** (verifier가 자동 필터).
- **involved_task_ids는 실제 존재하는 task만** (verifier 차단). LLM이 환각으로 task_id 만들면 결과 폐기.
- **금지 단어 필터** (담당자 인격 평가 등) — Narrator와 동일 룰.

### 6A.6 LLM 프롬프트

```
[SYSTEM]
You receive a project's tasks (title, description, delay_reason, status,
predecessors), milestones, and member roles. Your job: find soft risk
patterns that deterministic rules cannot catch. Output JSON only.

For each pattern you find, output:
- id: one of [S1, S2, S3, S4, S5]
- confidence in [0,1]
- involved_task_ids: list of EXISTING task_ids only
- supporting_facts: short Korean strings citing actual title/description text
- suggested_action: optional, must use the provided action vocab

Only emit a finding if confidence ≥ 0.5. Avoid speculative findings.
Do NOT judge people. Forbidden words: 매력, 호감, 성격, 게으, 무능, 책임감.

[USER]
Tasks: <list>
Milestones: <list>
Members: <list>
Action vocab: ["reschedule","reassign","split_task","raise_importance",
               "lower_importance","add_predecessor","remove_predecessor"]
Existing task_ids: <set>
Schema: { "soft_checks": [ { ... see §6A.4 ... } ] }
```

### 6A.7 검증 노드 (verify_soft_checks)

```python
def verify_soft_checks(items, snapshot) -> tuple[list, list[str]]:
    valid_ids = {t.task_id for t in snapshot.tasks}
    kept, violations = [], []
    for it in items:
        if it.confidence < 0.5:
            violations.append(f"low_confidence:{it.id}")
            continue
        if any(tid not in valid_ids for tid in it.involved_task_ids):
            violations.append(f"hallucinated_task_id:{it.id}")
            continue
        if has_forbidden_words(it.user_facing_text or ""):
            violations.append(f"forbidden_word:{it.id}")
            continue
        kept.append(it)
    return kept, violations
```

위반은 폐기되며, warnings에 기록된다. soft_checks가 0건이어도 hard checks는 항상 정상 동작.

## 7. 제안 생성 (Failed-check 1:1 매핑)

### 7.1 알고리즘
```
failed = [c for c in checks if c.applicable and c.result == "fail"]
candidates = []
for check in failed:
    action = check.fix_template(snapshot, priority, schedule)
    if action is not None:
        candidates.append((check, action))

# blocker fix는 우선
candidates.sort(key=lambda x: (not x[0].is_blocker,))   # blocker가 앞
top5 = candidates[:5]   # max 5개
```

### 7.2 액션 어휘 (고정 7종)

`07-data-contracts §1.5` 참조.
| action | 설명 |
|---|---|
| `reschedule` | 슬롯 변경 (Schedule Agent의 다른 candidate_slot 사용 또는 재분석 요청) |
| `reassign` | 담당자 변경 (overload 해소) |
| `split_task` | Task 분해 (큰 estimated_hours가 마감 안에 안 들어갈 때) |
| `raise_importance` | 중요도 상향 |
| `lower_importance` | 중요도 하향 |
| `add_predecessor` | 선행 의존 추가 |
| `remove_predecessor` | 선행 의존 제거 |

### 7.3 fix_template 예

```python
class WorkloadConcentration(Check):
    id = "workload_concentration"
    group = "workload"
    is_blocker = False

    def is_applicable(self, snap, prio, sch):
        return sch is not None and len(snap.members) > 0

    def evaluate(self, snap, prio, sch, now):
        return all(not w.is_overloaded
                   for w in compute_member_workloads(snap, sch, now))

    def evidence_facts(self, snap, prio, sch, now):
        overloaded = [w for w in compute_member_workloads(snap, sch, now) if w.is_overloaded]
        return [f"{w.member_id} utilization={w.utilization}" for w in overloaded]

    def fix_template(self, snap, prio, sch):
        # 가장 부하 큰 멤버 + 그의 가장 우선순위 낮은 task → 다른 멤버로 reassign
        overloaded_member = max(workloads, key=lambda w: w.utilization)
        candidate_task = lowest_priority_task_of(overloaded_member, prio)
        target_member = least_loaded_member()
        return Action(
            type="reassign",
            target_task_id=candidate_task.task_id,
            from_=overloaded_member.member_id,
            to=target_member.member_id,
        )
```

### 7.4 중복 액션 병합
같은 (target_task_id, action_type) 후보가 여러 체크에서 나오면 1개로 병합 (`fixes_check_ids` 다중 ID).

### 7.5 폐기 룰
- fix_template이 None을 반환 (해결책 추정 불가) → 폐기
- 같은 action을 2회 이상 제안하지 않도록 dedup
- 모든 후보 폐기 시 `suggestions: []` + summary에 "현재 큰 위험은 없습니다"

## 8. LLM Narrator (자연어화)

### 8.1 호출
- 입력: `failed_checks`, `task_risk_levels`, `member_workload`, `top5_suggestions`
- 출력 schema:
  ```json
  {
    "summary": "string (≤ 400자)",
    "suggestions_user_text": [
      {"id": "rs_xxx", "user_facing_text": "..."}
    ]
  }
  ```
- temperature=0, JSON 강제

### 8.2 프롬프트 제약
```
[SYSTEM]
You receive deterministic risk evaluation: failed checks (with evidence facts),
task risk levels, member workload utilization, and pre-computed suggestions
(action + facts).

Your job: phrase explanations and suggestion texts in Korean using ONLY the
provided facts and numbers. Do NOT invent numbers, do NOT add aesthetic
or personal judgments.

FORBIDDEN words: 매력, 호감, 인상, 성격, 잘생, 멋지, 게으, 느려, 의지,
무능, 책임감, 능력 (담당자 평가).
ALLOWED: cite numbers from facts, name the failed check IDs, name action types.

The summary covers the project status, not individual people.
```

### 8.3 후처리 검증
- 출력에 금지 단어 정규식 매칭 → 위반 시 1회 재시도 → fallback 룰 템플릿
- 숫자 인용 검증 (facts 안에 있는 숫자만)

## 9. LangGraph Sub-graph 구조

### 9.1 RiskState

```python
class RiskState(BaseModel):
    snapshot: ProjectSnapshot
    priority: PriorityResponse
    schedule: Optional[ScheduleResponse] = None
    now: datetime

    # 결정적 산출물
    checks: list[CheckResult] = []
    task_risk_levels: list[dict] = []
    member_workload: list[dict] = []
    blockers_failed: list[str] = []
    candidates: list[SuggestionCandidate] = []
    top5: list[SuggestionCandidate] = []

    # Soft checks (LLM 추론)
    soft_checks: list[SoftCheck] = []
    soft_check_violations: list[str] = []

    # Narrator
    summary: Optional[str] = None
    narrator_violations: list[str] = []
    narrator_retries: int = 0

    response: Optional[RiskResponse] = None
```

### 9.2 그래프 정의

```python
def build_risk_graph():
    g = StateGraph(RiskState)

    # 결정적 lane
    g.add_node("evaluate_checks",       node_evaluate_checks)
    g.add_node("compute_task_risks",    node_compute_task_risks)
    g.add_node("compute_workload",      node_compute_workload)
    g.add_node("generate_candidates",   node_generate_candidates)
    g.add_node("dedup_candidates",      node_dedup_candidates)

    # Soft check lane (LLM, 결정적 lane과 병렬)
    g.add_node("llm_soft_checks",       node_llm_soft_checks)        # LLM, t=0.2
    g.add_node("verify_soft_checks",    node_verify_soft_checks)     # 결정적

    # Narrator lane
    g.add_node("narrate",               node_narrate)                # LLM, t=0
    g.add_node("safety_filter",         node_safety_filter)
    g.add_node("pack_response",         node_pack_response)

    g.set_entry_point("__start__")

    # 결정적 lane (체인)
    g.add_edge("__start__",           "evaluate_checks")
    g.add_edge("evaluate_checks",     "compute_task_risks")
    g.add_edge("compute_task_risks",  "compute_workload")
    g.add_edge("compute_workload",    "generate_candidates")
    g.add_edge("generate_candidates", "dedup_candidates")

    # Soft lane (병렬 fan-out from start)
    g.add_edge("__start__",           "llm_soft_checks")
    g.add_edge("llm_soft_checks",     "verify_soft_checks")

    # 합류: 결정적 dedup + soft verify 끝나면 narrate
    g.add_edge(["dedup_candidates", "verify_soft_checks"], "narrate")
    g.add_edge("narrate",             "safety_filter")

    g.add_conditional_edges(
        "safety_filter",
        decide_after_safety,
        {"ok": "pack_response", "retry": "narrate", "fallback": "pack_response"},
    )
    g.add_edge("pack_response", END)
    return g.compile()

risk_subgraph = build_risk_graph()
```

**병렬 효과:** soft_checks LLM 호출(~3s)이 결정적 lane(~50ms)과 겹쳐 실행되므로, 전체 latency는 LLM lane에 의해 결정된다. soft_checks 없이도 결정적 lane이 항상 정상 동작.

### 9.3 분기 함수

```python
def decide_after_safety(state):
    if not state.narrator_violations:
        return "ok"
    if state.narrator_retries < 1:
        state.narrator_retries += 1
        return "retry"
    state.summary = rule_template_summary(state.checks, state.member_workload, state.top5)
    return "fallback"
```

### 9.4 노드 책임

| 노드 | 종류 | 책임 |
|---|---|---|
| `evaluate_checks` | 결정적 | 16개 Check 클래스 실행 |
| `compute_task_risks` | 결정적 | task_risk_level 룰 적용 |
| `compute_workload` | 결정적 | 7일 utilization |
| `generate_candidates` | 결정적 | failed check별 fix_template |
| `dedup_candidates` | 결정적 | 같은 (task, action) 병합 + Top-5 |
| `llm_soft_checks` | LLM (t=0.2) | 5종 soft check 패턴 추론 (배치 1회) |
| `verify_soft_checks` | 결정적 | confidence/task_id 환각/금지 단어 필터 |
| `narrate` | LLM (t=0) | summary + suggestion text + soft_check 요약 |
| `safety_filter` | 결정적 | 금지 단어 + 숫자 인용 검증 |
| `pack_response` | 결정적 | RiskResponse 패키징 (hard checks + soft_checks 분리 필드) |

### 9.5 Super-graph 노출

```python
# backend/app/agents/risk/__init__.py
from .graph import risk_subgraph
__all__ = ["risk_subgraph"]
```

## 10. 시뮬레이션 endpoint와의 공유

`POST /v1/projects/{id}/risk:simulate` 는 다음 노드만 재실행:
`evaluate_checks` → `compute_task_risks` → `compute_workload` → `dedup_candidates` → `pack_response_simulate`

LLM 미사용. < 100ms.

## 11. 테스트 전략

### 11.1 체크 단위 테스트
- 3개 체크 함수 각각 ≥ 4 케이스 (pass / fail / N/A / 경계값)
- 골든 입력 → 골든 결과 fixture로 회귀 검증

### 11.2 시나리오 테스트 (5개)
1. 정상 프로젝트 (모든 체크 pass) → blockers_failed=[], summary 긍정형
2. 마감 전 배치 불가 task → `deadline_feasibility` fail (blocker)
3. 한 명에게 일정이 몰림 → `workload_concentration` fail + reassign 제안
4. 순환 또는 선후행 마감 순서 오류 → `dependency_correctness` fail (blocker)
5. snapshot 변경 후 승인 → stale hash 감지

### 11.3 결정성 테스트
- 동일 입력 5회 → checks, task_risk_levels, member_workload 100% 동일 (hard lane)
- soft_checks는 t=0.2 → 5회 중 4회 이상 동일 ID 집합 목표 (≥ 80%)

### 11.4 Soft Check 안전성 테스트
- LLM이 환각 task_id 반환 → verify가 제거 검증
- LLM이 confidence 0.3 항목 반환 → 자동 폐기
- LLM이 금지 단어 사용 → 폐기
- timeout 4s 초과 시 soft_checks=[] 빈 배열 + warning 검증
- 5종 패턴별 골든 케이스 (의도적 트리거 입력) → 해당 ID가 결과에 포함되는지

### 11.5 LLM 안전성
- summary에 금지 단어 → 자동 재시도 → fallback
- 위반 0건 (CI gating)

### 11.6 Agentic 동작
- failed 체크 수와 candidates 수 일치 (dedup 후 ≤)
- top5 정렬: blocker fix가 항상 앞
- soft_checks는 hard checks/blockers_failed에 영향 없음 (회귀 검증)

## 12. 성능 목표

| 지표 | 목표 |
|---|---|
| 체크 평가 latency (Task 100개, hard lane) | ≤ 30ms |
| Workload 계산 latency | ≤ 10ms |
| Soft Check LLM latency P95 | ≤ 4s |
| Narrator latency P95 | ≤ 2.0s |
| 전체 Risk Agent latency P95 (병렬) | ≤ 5s |
| Schema Pass Rate | ≥ 98% |
| 결정성 (hard lane 5회 동일) | 100% |
| Soft Check 환각률 (verify로 잡힌 비율) | ≤ 10% |
| 금지 단어 검출률 | 100% |

## 13. 마일스톤

| 주차 | 산출물 |
|---|---|
| 1주차 | 마감/선후행 2개 체크 + task_risk_level 룰 + 단위테스트 |
| 2주차 | 담당자 부하 1개 체크 + member_workload + fix_template + dedup |
| 3주차 | Soft Checks (S1~S5) + verify_soft_checks + Narrator + safety_filter + 5 시나리오 통합 + simulate endpoint 공유 |

## 14. 다른 역할과의 인터페이스

- **Priority Agent**: tasks_priority의 score를 suggestion 대상 선정에 사용 (우선순위 재계산 금지).
- **Schedule Agent**: slot_proposals + unschedulable을 사용. schedule이 None이면 `workload_concentration`이 N/A.
- **Backend**: `risk_subgraph` 단일 진입점. simulate endpoint도 본 모듈의 함수 호출.
- **Frontend**:
  - `task_risk_levels`로 Task 카드 색상 (overdue=빨강 / at_risk=주황 / watch=노랑 / ok=초록)
  - `member_workload`로 담당자별 부하 막대 (1.0 초과는 빨강)
  - `blockers_failed`는 화면 상단 빨간 알림 영역
  - `suggestions`는 카드 리스트, `removes_blocker=true`인 카드 상단 고정
  - `soft_checks`는 hard 영역과 분리된 "AI 직관" 섹션. 각 항목 옆에 confidence 표시 (예: "78% 확신") + "PM이 확인" / "무시" 버튼. PM이 확인 시 suggested_action을 G3 폼 미리채움으로 전달.
  - `summary`는 대시보드 헤더 박스

## 15. 정직성 노트

- 본 Agent는 **종합 위험 점수가 없다.** 평균은 위험을 가린다 — blocker가 1건이라도 있으면 평균은 무관하다.
- 3개 hard check는 의도적으로 좁게 유지한다. 추가는 PR 합의 사항 (`08-roles-and-handoffs.md §3.5`).
- 입력 데이터 부족, 상태 정합성, 미할당 자체는 hard check가 아니라 PM 입력/soft check 영역으로 둔다.
- **soft_checks는 추측이다.** confidence와 supporting_facts를 항상 노출해 PM이 판단할 수 있게 한다. 결정적 hard checks와 절대 섞이지 않는다 — 이것이 안전성과 가치 모두를 잡는 방법.
- soft_checks 5종은 시작점이다. 운영하면서 false positive가 잦은 ID는 비활성, 가치 있는 패턴은 추가 (PR 합의).
