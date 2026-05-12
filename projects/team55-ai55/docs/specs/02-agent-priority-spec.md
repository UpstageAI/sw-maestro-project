# 02. Priority Agent — 사양

> 담당자: AI 개발 #1
> 책임: ProjectSnapshot → **결정적 우선순위 점수 + 미배정 Task 담당자 배정 + AI Task 분해 제안 + 자연어 설명**
> **Architecture**: Assign-and-Score (결정적 담당자 배정 + 결정적 5요소 가중합 + 선택적 LLM Task 분해 + LLM Narrator)

## 0. 이번 구현 의도 (필수)

이 spec은 기존 Priority Agent 문서를 그대로 재사용하는 것이 아니라, 현재 담당자가 구현해야 하는 실제 책임을 기준으로 한다.

Priority Agent가 반드시 끝내야 하는 일:

1. **모든 Task에 우선순위 점수를 매긴다.**
   - 마감이 가까운가?
   - PM이 중요하다고 표시했는가?
   - 선행 Task가 아직 끝나지 않아 막혀 있는가?
   - 기대 진척보다 늦고 있는가?
2. **Task 순위를 정한다.**
   - `rank=1`이 PM이 가장 먼저 볼 Task다.
   - 동점이면 `task_id`로 안정 정렬해 같은 입력에서 항상 같은 순서가 나온다.
3. **왜 그 순위인지 evidence를 남긴다.**
   - 각 Task는 최소 5개 evidence fact를 가진다.
   - fact에는 마감, 중요도, 선행 미완료, 기대/실제 진척, 담당자 부하가 드러나야 한다.
4. **큰 Task 분해 제안을 만든다.**
   - PM이 `request_decomposition_for`로 요청한 Task만 분해한다.
   - 실제 Task 생성은 하지 않는다. PM 승인 전까지는 제안만 반환한다.
5. **미배정 Task 담당자를 실제 배정한다.**
   - `todo` / `in_progress` 중 `assignee_id=null`인 Task만 대상이다.
   - 이미 담당자가 있는 Task는 절대 바꾸지 않는다.
   - Task title/description의 역할 단서를 member.role과 매칭하고, 매칭이 없으면 현재 부하가 가장 낮은 member에게 배정한다.
   - 배정 결과는 `PriorityResponse.task_assignments`에 근거와 함께 기록되고, downstream schedule/risk가 배정된 담당자를 사용한다.
6. **LLM은 설명과 분해만 담당한다.**
   - priority score, rank, assignee_id는 결정적 코드가 계산/선택한다.
   - LLM은 rationale 문장과 요청된 decomposition만 만든다.
   - 없는 숫자, 없는 task_id, 사람 평가 표현은 차단하고 fallback한다.

## 1. Agent로 분류되는 근거

본 모듈은 단일 LLM 호출이 아닌 **에이전틱 워크플로우**를 가진다.

| Agentic 속성 | 본 Agent 구현 |
|---|---|
| **Tool use** | DAG 검증, 마감 임박도 계산, 담당자 자동 배정, 담당자 부하 계산 등 결정적 도구 호출 |
| **Self-critique** | 담당자 배정은 존재하는 member_id만 허용하고, 분해 결과는 schema verifier로 검증한다 |
| **Multi-step** | Validate snapshot → Assign unassigned active tasks → Compute priority (결정적) → Decompose (선택) → Narrate |
| **Adaptive routing** | 분해 요청이 없으면 LLM 분해 단계 skip, 모두 결정적 |
| **결정성 유지** | LLM은 "Task 분해"와 "자연어 설명"만, 점수 계산은 모두 순수 함수 |

## 2. 책임 (Responsibilities)

1. ProjectSnapshot 입력 검증 (DAG 정합성 등)
2. `todo` / `in_progress` 중 담당자가 없는 Task를 역할 단서 + 현재 부하 기준으로 실제 담당자에게 배정
3. 모든 Task의 우선순위 점수 산출 (4개 핵심 신호 + 담당자 부하 보정, 결정적)
4. 모든 Task의 `rank` 산출
5. Task별 결정적 `evidence_facts` 생성
6. (선택) PM이 분해 요청한 Task에 대해 LLM이 2~8개 subtask 제안
7. LLM Narrator로 facts를 한국어 자연어로 포장
8. `tasks_priority`, `task_assignments`, `task_decompositions`, `warnings`, `agent_meta`를 포함한 PriorityResponse 반환

## 3. 비-책임 (명시적 금지)

| 금지 항목 | 이유 |
|---|---|
| Task의 importance를 변경 | PM 입력 그대로 사용 |
| Task의 estimated_hours를 LLM이 단일 값으로 추정 | 분해 시에도 항상 [min, max] 범위로 |
| 슬롯 배치 (datetime 결정) | Schedule Agent의 책임 |
| 마감 리스크 / 과부하 알림 | Risk Agent의 책임 |
| 담당자 평가 ("이 사람은 느리다") | 본 spec 명시적 금지 |
| 자연어 설명에서 facts에 없는 숫자 인용 | 사실 보고형 위반 |
| Task 자동 생성 (분해 결과를 바로 Task로 INSERT) | G3 게이트 위반 — PM이 폼에서 승인 후 입력 |
| 이미 담당자가 있는 Task 재배정 | 기존 담당자 변경은 Risk Agent의 reassign 제안 영역과 충돌 방지 |

## 4. 입력 / 출력

### 4.1 Input
```python
class PriorityRequest(BaseModel):
    snapshot: ProjectSnapshot
    request_decomposition_for: list[str] = []  # task_id 목록 (비면 분해 skip)
    now: datetime  # 결정성 보장을 위해 외부에서 주입 (Backend가 채움)
```

### 4.2 Output
`07-data-contracts.md §3` 의 PriorityResponse schema 100% 준수.

필수 출력:
- `tasks_priority`: 모든 Task의 점수, rank, factors, evidence, rationale
- `task_assignments`: 이번 priority 실행에서 자동 배정한 Task 목록. 미배정 active Task가 없으면 빈 배열.
- `task_decompositions`: PM이 요청한 Task 분해 제안. 요청이 없거나 검증 실패 시 빈 배열.
- `warnings`: 순환 의존, LLM fallback, 분해 실패 등
- `agent_meta`: LLM 호출 수와 schema retry 수

### 4.3 Analyze 결과의 Task 반영 계약

`POST /analyze` 성공 후 Frontend는 PriorityResponse를 단순 표시 캐시로만 두지 않고, 다음 값을 local project Task 객체에 반영한다.

- `task_assignments[]`는 해당 Task의 `assignee_id`에 반영한다. 단, 실제 Task 필드 변경으로 인정되는 것은 analyze 입력 시점에 `assignee_id=null`이고 `status in ("todo", "in_progress")`였던 Task뿐이다.
- 이미 담당자가 있던 Task, 또는 `blocked`, `review`, `done`, `cancelled` 상태 Task의 `assignee_id`는 Priority 결과로 절대 덮어쓰지 않는다.
- `tasks_priority[]`의 `score`, `rank`, `evidence_facts`, `rationale`, `factors`는 Task에 붙는 **derived analysis fields**다. PM이 직접 소유한 입력 필드가 아니며, 분석 결과를 보여주기 위한 읽기 전용 값이다.
- derived analysis fields는 snapshot stale fingerprint를 dirty로 만들면 안 된다. 즉 `score`, `rank`, `evidence_facts`, `rationale`, `factors`만 갱신된 경우 재분석 트리거가 발생하지 않아야 한다.
- PM-owned fields(`title`, `description`, `importance`, `deadline`, `estimated_hours`, `progress_percent`, `status`, `predecessor_ids` 등)는 Priority Agent가 변경하지 않는다. 분해 결과도 PM 승인 전까지 Task 생성/수정으로 간주하지 않는다.

## 5. 도구 (Tools) — 결정성 분류

### 5.1 결정적 도구 (Tools, 순수 함수)

| Tool | 입력 | 출력 | 구현 |
|---|---|---|---|
| `validate_dag(tasks)` | Task[] | `{ok: bool, cycle_path?: list[str]}` | NetworkX 또는 자체 구현, Tarjan 알고리즘 |
| `compute_deadline_pressure(task, now, project)` | task + now | `[0,1]` 정규화 점수 | 룩업 룰 (아래 §6.2) |
| `compute_predecessor_pressure(task, all_tasks)` | task + DAG | `[0,1]` 점수 | 미완 선행 수 / 전체 선행 수 |
| `compute_progress_gap(task, now)` | task + now | `[0,1]` 점수 | (기대 진척률 - 실제 진척률) clamp [0,1] |
| `compute_overload_penalty(task, all_tasks)` | task + tasks | `[0,1]` 점수 | 배정된 담당자의 동시 진행 task 수 또는 미배정 active Task 감점 |
| `assign_missing_assignees(tasks, members)` | Task[] + Member[] | TaskAssignment[] | 미배정 active Task를 역할 키워드 매칭 후 부하가 낮은 member에게 배정 |
| `verify_decomposition(decomp, source_task)` | TaskDecomposition + Task | `violations[]` | subtask sum/max in [0.7, 1.3]*source.estimated_hours |

### 5.2 LLM 도구

| Tool | 호출 횟수 | 모델 | temperature |
|---|---|---|---|
| `llm_decompose_task(task, project_context)` | 0~N회 (요청 task 수만큼) | Upstage Solar (또는 동등) | 0 |
| `llm_narrate(scores, facts)` | 1회 | Upstage Solar | 0 |

**호출 0회 경로**: 분해 요청이 없고, Narrator가 fallback 템플릿으로 충분한 경우 (예: 모든 facts가 "마감 N일 / 진척률 N%" 패턴이면 룰로 생성). MVP는 Narrator는 항상 호출.

## 6. 결정적 점수 정책 (가장 중요)

Priority score는 “PM이 먼저 봐야 할 순서”를 만들기 위한 결정적 점수다. LLM은 이 점수에 개입할 수 없다.

핵심 판단 질문:
- 마감이 가까운가? → `deadline_pressure`
- PM이 중요하다고 표시했는가? → `importance`
- 선행 Task가 아직 끝나지 않아 막혀 있는가? → `predecessor_pressure`
- 기대 진척보다 늦고 있는가? → `progress_gap`
- 이미 배정된 담당자에게 일이 너무 몰려 있는가? → `overload_penalty`

### 6.1 종합 우선순위
```python
def priority(task, snapshot, now, weights=DEFAULT_WEIGHTS):
    f = {
        "deadline_pressure":    deadline_pressure(task, now, snapshot.project),
        "importance":           importance_score(task),
        "predecessor_pressure": predecessor_pressure(task, snapshot.tasks),
        "progress_gap":         progress_gap(task, now),
        "overload_penalty":     overload_penalty(task, snapshot.tasks),
    }
    raw = (
        weights.w_d * f["deadline_pressure"] +
        weights.w_i * f["importance"] +
        weights.w_p * f["predecessor_pressure"] +
        weights.w_g * f["progress_gap"] -
        weights.w_o * f["overload_penalty"]
    )
    return clamp_round(raw * 100, 0, 100), f
```

`DEFAULT_WEIGHTS` (변경은 PR 합의):
```
w_d = 0.35  # deadline_pressure  — 가장 큰 신호
w_i = 0.25  # importance         — PM의 명시적 의도
w_p = 0.15  # predecessor_pressure
w_g = 0.15  # progress_gap (지연)
w_o = 0.10  # overload_penalty (감점)
```
합 = 1.00 (overload는 음의 부호로 차감, 감점 상한 10).

### 6.2 deadline_pressure (룩업 룰)
```python
def deadline_pressure(task, now, project):
    if task.deadline is None:
        return 0.20   # 없으면 보수적 기본값
    days_left = business_days_between(now, task.deadline, project.timezone)
    if days_left <= 0:   return 1.00      # 초과
    if days_left < 1:    return 0.95
    if days_left < 3:    return 0.80
    if days_left < 7:    return 0.60
    if days_left < 14:   return 0.40
    if days_left < 30:   return 0.20
    return 0.10
```

### 6.3 importance_score (명시적 매핑)
```
critical → 0.95
high     → 0.75
medium   → 0.50
low      → 0.20
```

### 6.4 predecessor_pressure
```python
def predecessor_pressure(task, all_tasks):
    preds = [t for t in all_tasks if t.task_id in task.predecessor_ids]
    if not preds:
        return 0.0
    incomplete = sum(1 for p in preds if p.status not in ("done", "cancelled"))
    return incomplete / len(preds)
```

### 6.5 progress_gap
선형 기대 진척률 모델:
```python
def progress_gap(task, now):
    if task.deadline is None or task.created_at is None:
        return 0.0
    span = (task.deadline - task.created_at).total_seconds()
    if span <= 0: return 0.0
    elapsed = max(0, (now - task.created_at).total_seconds())
    expected = min(100, 100 * elapsed / span)
    actual = task.progress_percent
    if actual >= expected: return 0.0
    return clamp((expected - actual) / 100, 0, 1)
```

### 6.6 overload_penalty

담당자 미정 Task는 Step 1에서 먼저 담당자를 배정한 뒤 점수를 계산한다. 따라서 active Task가 담당자 없이 남는 경우는 member가 아예 없거나 배정 불가능한 예외 경로다.

```python
def overload_penalty(task, all_tasks):
    assignee_id = task.assignee_id
    if assignee_id is None and task.status in ("todo", "in_progress"):
        return 1.0      # member가 없어 배정하지 못한 active Task는 미배정 자체를 최대 감점
    if assignee_id is None:
        return 0.0
    in_progress = sum(1 for t in all_tasks
                      if t.assignee_id == assignee_id
                      and t.status in ("todo", "in_progress"))
    # 동시 6개 이상이면 만점 (감점 1.0)
    return clamp(in_progress / 6, 0, 1)
```

### 6.7 evidence_facts 생성

각 Task의 PriorityScore에는 다음 5개 fact가 항상 포함된다:
```
"마감까지 영업일 기준 D=1.5일"        (deadline_pressure)
"중요도=high (점수 0.75)"             (importance)
"미완 선행 1/2건"                    (predecessor_pressure)
"기대 진척률 60% / 실제 30%"          (progress_gap)
"담당자 동시 진행 4개"                (overload_penalty)
```
`progress_gap`이 0이면 "기대 대비 진척 양호" 같은 보수적 fact.

### 6.8 담당자 자동 배정

대상:
- `task.assignee_id is None`
- `task.status in ("todo", "in_progress")`

비대상:
- 이미 담당자가 있는 Task
- `blocked`, `review`, `done`, `cancelled` 상태 Task

알고리즘:
```python
def assign_missing_assignee(task, members, all_tasks):
    role_hint = infer_role_hint(task.title + " " + task.description)
    candidates = score_member_role_match(role_hint, members)
    if max(role_match_score) > 0:
        pool = members with best role_match_score
    else:
        pool = all members
    return member in pool with lowest active_load
```

역할 단서 예:
- frontend: `frontend`, `front`, `react`, `ui`, `ux`, `page`, `component`, `화면`, `페이지`, `컴포넌트`
- backend: `backend`, `server`, `api`, `fastapi`, `db`, `schema`, `auth`, `서버`, `데이터베이스`, `인증`
- design: `design`, `figma`, `wireframe`, `prototype`, `디자인`, `피그마`
- qa: `qa`, `test`, `testing`, `quality`, `검증`, `테스트`
- data: `data`, `analytics`, `metric`, `report`, `데이터`, `분석`, `지표`

동률 처리:
1. role match score 높은 member
2. active load utilization 낮은 member
3. active Task 수 적은 member
4. `member_id` 사전순

출력:
- `Task.assignee_id`를 실제로 채운다. 단, 실제 변경 대상은 입력 시점에 미배정 active Task였던 항목뿐이다.
- `PriorityResponse.task_assignments[]`에 `task_id`, `assignee_id`, `rationale_facts`, `rationale`을 기록한다.
- `tasks_priority[]`의 점수/rank/evidence/rationale은 Frontend가 Task 객체에 derived analysis fields로 붙일 수 있지만, PM-owned fields나 snapshot stale fingerprint에는 영향을 주지 않는다.

## 7. 워크플로우

```
┌─────────────────────────────────────────────────────────┐
│ Step 0: Snapshot 검증                                    │
│   validate_dag(tasks) → 순환 발견 시 즉시 422            │
│   필수 필드 체크: title/importance 누락 시 422            │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 1: 미배정 active Task 담당자 배정                    │
│   assignee_id=null AND status in todo/in_progress          │
│   role hint(title/description) → member.role match         │
│   동률/무매칭이면 active load 낮은 member 선택             │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 2: 우선순위 점수 (모든 Task, 결정적)                  │
│   for task in tasks:                                     │
│     score, factors = priority(task, snapshot, now)       │
│     facts = build_facts(task, factors)                   │
│   ranks = sort_desc(scores)                              │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 3 (선택): Task 분해                                  │
│   for task_id in request.request_decomposition_for:      │
│     llm_decompose_task(task, project)                    │
│     verify_decomposition() → 위반 시 재시도 1회 → skip   │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 4: Narrator (LLM, t=0)                              │
│   llm_narrate(top_10_priority, facts)                    │
│   → rationale 200자 이내, facts/숫자만 인용              │
│   safety_filter: 금지 단어 정규식 → 위반 시 1회 재시도    │
│                  → fallback: 룰 템플릿                   │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
              결과 반환
```

### 7.1 종료 조건
- Step 1 담당자 배정은 member가 있으면 결정적으로 완료한다.
- Step 2 점수/rank/evidence는 항상 완료한다.
- Step 3 LLM 분해 요청은 task 수에 비례하고, 5개 초과 분해 요청은 422.
- Step 4 narrator는 top-10 Task만 LLM으로 설명하고, 나머지는 룰 템플릿 rationale을 유지한다.
- Step 4 narrator latency > 3s → 룰 fallback.

## 8. Verifier 상세

### 8.1 verify_decomposition
```
input: decomp{subtasks[]}, source_task
algorithm:
  1. subtask 수 ∈ [2, 8] 아니면 violation
  2. 모든 subtask의 estimated_hours_range[0] ≤ range[1]
  3. sum(min) ≤ source.estimated_hours * 1.3
  4. sum(max) ≥ source.estimated_hours * 0.7
  5. suggested_predecessors_within_decomposition가 0..len-1 범위
  6. DAG 안 순환 (분해 내부)
output: violation 목록 또는 빈 배열
```

### 8.2 verify_dag (전체 Task)
- Tarjan SCC로 순환 검출
- 발견 시 `circular_dependency:<path>` warning 추가. Backend는 `/analyze`를 계속 진행하고 Risk `dependency_correctness`가 blocker로 노출한다.

### 8.3 verify_priority_determinism (테스트용)
- 동일 snapshot + now에 대해 5회 호출 → score, factors, ranks 100% 동일

## 9. LLM 프롬프트 설계

### 9.1 llm_decompose_task
```
[SYSTEM]
You decompose a Task into 2~8 subtasks. Output JSON ONLY matching the
provided schema. Each subtask has estimated_hours_range as [min, max]
to express uncertainty. Do NOT output single point estimates.

The total of (sum of min) and (sum of max) must roughly match the source
task's estimated_hours within ±30%.

Do NOT infer importance or deadline. Do NOT assign generated subtasks to people.
Priority's deterministic assignment step may assign the source Task only when it
is currently unassigned and active.
Do NOT use words: 매력, 호감, 인상, 성격, 잘생, 멋지.
Use Korean for titles/descriptions.

[USER]
Source task: <task json>
Project goal: <project.goal>
Member roles available: <member roles>
Return JSON: <schema>
```

### 9.2 llm_narrate (Top-10 priority)
```
[SYSTEM]
You receive deterministic priority scores and evidence facts (numbers only).
Phrase each task's rationale in Korean using ONLY the provided facts.

ALLOWED: cite numbers from facts, name the dominant factor.
FORBIDDEN: invent numbers, judge the assignee, use forbidden words below.
Forbidden words: 매력, 호감, 인상, 성격, 잘생, 멋지, 게으, 느려, 의지.

Each rationale ≤ 200 chars.

[USER]
Tasks (top 10): <json with score + facts>
Return JSON: { "rationales": [{ "task_id": "...", "text": "..." }] }
```

## 10. 실패 모드 / Fallback

| 상황 | 처리 |
|---|---|
| 순환 의존 | priority warning 추가 + Risk `dependency_correctness` fail |
| importance / status 누락 | 422 task_info_insufficient |
| estimated_hours 누락 | priority는 계산 가능 (deadline + importance 위주). warning 추가, 분해 요청 시 422. |
| 담당자 없는 active Task | Priority가 role hint + 부하 기준으로 배정하고 `task_assignments`에 기록 |
| role hint 없음 또는 매칭 실패 | 가장 낮은 active load의 member에게 배정 |
| member 없음 | 배정 skip + schedule/risk가 기존 미배정 경로 처리 |
| LLM 분해 schema 위반 | 재시도 1회 → 실패 시 해당 Task 분해 skip + warnings에 추가 |
| LLM Narrator 실패 / 금지 단어 | 재시도 1회 → 실패 시 룰 템플릿 fallback (예: "마감까지 1.5일 + 중요도 high → 우선") |
| Total latency > 4s | Narrator 룰 fallback 즉시 적용 |

## 11. LangGraph Sub-graph 구조

### 11.1 PriorityState

```python
class PriorityState(BaseModel):
    snapshot: ProjectSnapshot
    now: datetime
    request_decomposition_for: list[str] = []

    # Step 0
    dag_valid: bool = False
    dag_violations: list[str] = []

    # Step 1 산출물
    task_assignments: list[TaskAssignment] = []

    # Step 2 산출물
    priority_scores: list[PriorityScore] = []

    # Step 3 산출물
    decompositions: list[TaskDecomposition] = []
    decomp_violations: list[str] = []

    # Step 4 산출물
    rationales: dict[str, str] = {}
    narrator_violations: list[str] = []
    narrator_retries: int = 0

    # 메타
    warnings: list[str] = []
    tool_call_log: list[dict] = []
```

### 11.2 그래프 정의

```python
from langgraph.graph import StateGraph, END

def build_priority_graph():
    g = StateGraph(PriorityState)

    g.add_node("validate_snapshot",  node_validate_snapshot)   # 결정적
    g.add_node("assign_missing_assignees", node_assign_missing_assignees) # 결정적
    g.add_node("compute_priority",   node_compute_priority)    # 결정적
    g.add_node("decompose_tasks",    node_decompose_tasks)     # LLM (선택)
    g.add_node("narrate",            node_narrate)             # LLM
    g.add_node("safety_filter",      node_safety_filter)       # 결정적
    g.add_node("pack_response",      node_pack_response)       # 결정적

    g.set_entry_point("validate_snapshot")

    g.add_conditional_edges(
        "validate_snapshot",
        decide_after_validate,
        {
            "ok":      "assign_missing_assignees",
            "invalid": END,    # 422는 Backend가 변환
        }
    )

    g.add_edge("assign_missing_assignees", "compute_priority")
    g.add_conditional_edges(
        "compute_priority",
        decide_after_priority,
        {
            "needs_decomp": "decompose_tasks",
            "skip_decomp":  "narrate",
        }
    )
    g.add_edge("decompose_tasks", "narrate")
    g.add_edge("narrate", "safety_filter")

    g.add_conditional_edges(
        "safety_filter",
        decide_after_safety,
        {
            "ok": "pack_response",
            "retry": "narrate",
            "fallback": "pack_response",
        }
    )

    g.add_edge("pack_response", END)
    return g.compile()

priority_subgraph = build_priority_graph()
```

### 11.3 분기 함수

```python
def decide_after_validate(state):
    if not state.dag_valid:
        return "invalid"
    return "ok"

def decide_after_priority(state):
    return "needs_decomp" if state.request_decomposition_for else "skip_decomp"

def decide_after_safety(state):
    if not state.narrator_violations:
        return "ok"
    if state.narrator_retries < 1:
        state.narrator_retries += 1
        return "retry"
    state.rationales = rule_template_rationales(state.priority_scores)
    state.warnings.append("narrator_fallback_template")
    return "fallback"
```

### 11.4 노드 책임

| 노드 | 종류 | 책임 |
|---|---|---|
| `validate_snapshot` | 결정적 | DAG 순환 + 필수 필드 + estimated_hours 누락 추적 |
| `assign_missing_assignees` | 결정적 | 미배정 active Task를 role hint + load 기준으로 기존 member에게 배정 |
| `compute_priority` | 결정적 | 5요소 점수 + ranks + facts 빌드 |
| `decompose_tasks` | LLM | 요청 task별 2~8개 subtask 제안 + verify_decomposition |
| `narrate` | LLM (t=0) | rationale (≤200자, facts 인용만) |
| `safety_filter` | 결정적 | 금지 단어 정규식 + 인용 숫자 검증 |
| `pack_response` | 결정적 | PriorityResponse 패키징 |

### 11.5 Super-graph 노출

```python
# backend/app/agents/priority/__init__.py
from .graph import priority_subgraph
__all__ = ["priority_subgraph"]
```

## 12. 테스트 전략

### 12.1 단위 테스트
- 각 결정적 함수 (deadline_pressure, importance_score, ...): pass / fail / 경계값 ≥ 4 케이스
- assign_missing_assignees: role hint 매칭 / 무매칭 load fallback / 기존 assignee 보존
- verify_decomposition: 정상 / 시간 합 위반 / 순환 / subtask 수 위반 / predecessor 인덱스 범위 위반
- DAG validator: 단일 순환 / 다중 순환 / 자기 참조 / 정상

### 12.2 골든 셋
- `tests/fixtures/priority/` — 8개 시나리오 input + expected priority/ranks/assignments
  1. 마감 임박 1개 + 보통 2개 → 임박 task가 rank 1
  2. 모든 마감 동일, 중요도 차이 → critical이 rank 1
  3. 선행 미완 task → predecessor_pressure 발동
  4. 진척률 50% / 기대 80% → progress_gap 발동
  5. 한 명에게 6개 몰림 → overload_penalty 감점
  6. frontend 단서가 있는 미배정 active Task → frontend role member에게 배정
  7. 역할 단서가 없는 미배정 active Task → active load가 가장 낮은 member에게 배정
  8. 이미 assignee_id가 있는 Task → 기존 담당자 유지, task_assignments에 미포함

### 12.3 결정성 테스트
- 동일 (snapshot, now) 5회 호출 → task_assignments, priority_scores, ranks, factors 100% 동일

### 12.4 LLM 안전성
- Narrator 출력에 금지 단어 → 자동 재시도 → 자동 fallback
- facts에 없는 숫자 인용 검출 → fallback
- 위반 0건 (CI gating)

### 12.5 Agentic 동작
- decomposition_calls 분포: 요청한 task 수와 일치
- narrator_calls 분포: 정상 1회, 재시도 ≤ 5%, fallback ≤ 1%
- assignment_calls 분포: LLM 호출 0회, 미배정 active Task 수와 task_assignments 수 일치

## 13. 성능 목표

| 지표 | 목표 |
|---|---|
| 담당자 배정 + 점수 계산 latency (Task 100개, Member 20명) | ≤ 50ms |
| 분해 LLM 호출 (1 task) | ≤ 2.0s |
| Narrator latency P95 (top-10) | ≤ 2.0s |
| Schema Pass Rate (분해 + narrate) | ≥ 98% |
| 결정성 (5회 동일) | 100% |

## 14. 마일스톤

| 주차 | 산출물 |
|---|---|
| 1주차 | 결정적 함수 5종 + 담당자 자동 배정 + DAG validator + 골든 8케이스 통과 + LangGraph 골격 |
| 2주차 | LLM 분해 노드 + verify_decomposition + 분기 함수 + schema 검증 |
| 3주차 | Narrator + safety_filter + 룰 fallback + 담당자 보존/배정 결정성 회귀 테스트 |

## 15. 다른 역할과의 인터페이스

- **Backend**: `priority_subgraph` 단일 진입점. now는 Backend가 채워서 주입 (테스트용 결정성).
- **Schedule Agent**: Priority가 채운 `snapshot.tasks[].assignee_id`와 `PriorityResponse.tasks_priority.score`를 받아 슬롯 후보 우선순위 결정.
- **Risk Agent**: Priority가 채운 담당자와 `PriorityResponse.tasks_priority.factors.progress_gap`을 직접 사용 (중복 계산 방지).
- **Frontend**: `task_assignments`를 local project Task에 반영한 뒤 `tasks_priority`를 Task의 derived analysis fields로 붙이고 rank 순 리스트로 표시. factors를 작은 차트(5개 막대)로. rationale을 카드 본문으로. derived analysis fields 갱신만으로 stale fingerprint를 dirty 처리하지 않는다.

## 16. 정직성 노트

- LLM은 **추정에 약하다**. 그래서 estimated_hours 분해도 단일 값이 아닌 [min, max] 범위로 강제한다.
- 점수 가중치는 **튜닝하지 않는다** (튜닝하기 시작하면 결정성과 설명력이 동시에 깨진다). 골든 셋에서 분포가 이상하면 가중치를 바꾸지 말고 골든 셋의 라벨을 재검토한다.
- 본 Agent는 PM의 입력(importance, deadline, predecessor_ids)을 **신뢰**한다. 입력이 잘못되면 출력도 잘못된다 — 이것은 버그가 아니라 설계.
