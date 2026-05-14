# 03. Schedule Agent — 사양

> 담당자: AI 개발 #2
> 책임: PriorityResponse + Snapshot → **실제 캘린더처럼 동작하는 Task별 후보 슬롯 + 충돌/의존성/몰림 검증 + LLM 재정렬된 추천 인덱스**
> **Architecture**: Hybrid — 결정적 Schedule Engine + 제한적 repair + 결정적 안전 floor + **LLM Reranker** (후보 index 선택 + rationale)

## 1. Agent로 분류되는 근거

본 Agent는 **결정적 도구 + LLM Reranker** 하이브리드 구조다. 결정적 레이어가 안전 floor를 보장하고, LLM은 그 floor를 통과한 후보들 중 어느 것이 PM의 직관에 더 맞는지를 판단한다.

| Agentic 속성 | 본 Agent 구현 |
|---|---|
| **Tool use** | 영업일/근무가능시간 계산, 충돌 검사, 슬롯 패킹 등 결정적 도구 6종 |
| **Self-critique** | 후보 슬롯이 (1) 충돌 없음 (2) 근무 안 (3) 선행 완료 후 — 3개 조건 검증 |
| **Multi-step** | priority-aware DAG ordering → greedy pack → 제한적 repair → final validation → **LLM Rerank** → final validation |
| **Adaptive routing** | LLM 재정렬이 안전 검증을 통과하면 채택, 실패하면 결정적 fit_score 순위로 fallback |
| **결정적 안전 floor** | 모든 selected slot은 결정적 검증(담당자 hard overlap 없음·근무시간 안·선행 종료 후·deadline 안·1시간 bucket 최대 2개)을 통과해야 한다. LLM은 폐기·생성 권한 없음, **후보 index 선택만** 변경 |

이 설계로 응답이 충분히 빠르고(LLM 호출 1회/세션, 재정렬은 전체 batch 1회), 안전성도 보존된다.

## 2. 책임

1. PriorityResponse를 입력으로 받아 dependency를 깨지 않는 priority-aware topo 순서로 Task 배치
2. 후보 슬롯의 결정적 fit_score 산출 + quality 등급
3. 캘린더 충돌 검사 (`approved=true` 이벤트 + `external_blocking`)
4. 선행 Task가 이번 schedule run에서 함께 배치되면 후행 Task를 선행 selected slot 종료 후로 강제
5. 근무가능시간(요일/시간 윈도우) 안에서만 패킹
6. unschedulable Task와 사유를 명시적으로 반환
7. **LLM Reranker**: 결정적 floor를 통과한 top-K 후보를 Task 의미·맥락 기반으로 재정렬 + 1문장 rationale
8. **재정렬 안전 검증**: LLM이 새로 만든 슬롯이 없는지, 폐기한 슬롯이 없는지, 전역 schedule invariant를 깨지 않는지 검증
9. 같은 담당자 hard overlap은 금지하고, 다른 담당자 병렬은 허용하되 1시간 bucket에 selected task가 3개 이상 몰리면 repair 대상 처리

## 3. 비-책임 (명시적 금지)

| 금지 항목 | 이유 |
|---|---|
| 캘린더 INSERT 실행 | G2 게이트 — Backend가 PM 승인 후 처리 |
| 외부 캘린더 호출 (Google Calendar 등) | MVP 제외 (원본 기획서 84,96행) |
| LLM이 새 슬롯 생성 / 결정적 후보 폐기 | 안전 floor 위반 — Reranker는 **순서만** 변경 |
| LLM이 슬롯의 datetime을 수정 | 시간 산술은 결정적 도구 책임 |
| Task의 estimated_hours 추정 | Priority Agent의 분해 또는 PM 입력만 사용 |
| 담당자 자동 변경 | Risk Agent의 reassign 제안만, 변경은 PM |
| 마감 무시 슬롯 배치 | selected slot은 deadline을 넘기지 않는다. 불가 시 unschedulable |
| Risk PM 조치 문구 생성 | `PM 조치:` 수준의 액션 문구는 Risk Agent 책임 |
| 긴 Task를 여러 calendar event로 분할 | 현재 MVP contract는 task 하나 = selected slot 하나. `task_blocks()`는 유틸로 유지하되 응답 분할은 다음 범위 |

## 4. 입력 / 출력

### 4.1 Input
```python
class ScheduleRequest(BaseModel):
    snapshot: ProjectSnapshot
    priority: PriorityResponse  # priority_subgraph 결과
    horizon_days: int = 14       # 후보 슬롯 검색 기간
    now: datetime
    options: ScheduleOptions = ScheduleOptions()

class ScheduleOptions(BaseModel):
    max_candidates_per_task: int = 3
    prefer_morning: bool = False
    minimum_block_minutes: int = 30
    maximum_block_minutes: int = 240  # 4시간 단위 분할
```

### 4.2 Output
`07-data-contracts.md §4`의 ScheduleResponse schema 100% 준수.

## 5. 도구 (Tools)

### 5.1 결정적 도구 (Tools, 순수 함수)

| Tool | 입력 | 출력 | 구현 |
|---|---|---|---|
| `priority_aware_topo_sort(tasks, priority)` | Task[] + priority score | sorted Task[] | indegree 0 후보 중 `(-priority_score, task_id)` 순으로 선택하는 Kahn 알고리즘 |
| `expand_working_windows(member, project, range)` | member + 기간 | DateRange[] (요일·근무시간 적용) | 룩업 + 룰 |
| `task_blocks(task, options)` | task | block size 분 단위 list | 분석 유틸. 현재 MVP 후보 슬롯 길이는 `estimated_hours` 통째 |
| `find_candidate_slots(task, windows, conflicts)` | task + windows + 충돌이벤트 | CandidateSlot[] | greedy left-pack |
| `compute_fit_score(slot, task, member)` | slot + 컨텍스트 | int [0,100] | 가중합 (§6.2) |
| `detect_conflicts(slot, calendar_events)` | slot + 이벤트들 | conflict[] | 인터벌 오버랩 |
| `validate_selected_schedule(proposals, snapshot)` | proposals + snapshot | `violations[]` | selected_index, same-assignee hard overlap, dependency order, deadline, working window, density 검증 |
| `repair_schedule(proposals, blocked_context)` | proposals + 원인 | proposals | dependency chain + same-assignee 배치의 2순위/3순위 후보를 제한적으로 재시도 |
| `verify_rerank(original, payload)` | 원본 proposals + LLM payload | `violations[]` | task/index 순열 + selected index + 전역 invariant 검증 |

### 5.2 LLM 도구

| Tool | 호출 횟수 | 모델 | temperature |
|---|---|---|---|
| `llm_rerank_slots(tasks_with_candidates, project_context)` | 1회 (배치, 모든 Task의 후보를 한 번에) | Upstage Solar | 0 |

LLM은 **후보 index 선택만** 한다. 새 슬롯 생성/datetime 수정/슬롯 폐기/전역 invariant 위반은 verify_rerank가 차단하며, 하나라도 위반하면 전체 deterministic 결과로 fallback한다.

## 6. 결정적 알고리즘 (가장 중요)

### 6.1 메인 패킹 절차

```
SCHEDULE(snapshot, priority, horizon, now):
  ordered = priority_aware_topo_sort(snapshot.tasks, priority)

  earliest_start_by_task = {}   # 선행 완료 시각

  for task in ordered:
    if task.status in ("done", "cancelled"): continue
    if task.estimated_hours is None:
        unschedulable.add(task, "estimated_hours_missing")
        continue
    if task.assignee_id is None:
        unschedulable.add(task, "assignee_missing")
        continue

    if has_predecessor_not_scheduled_in_this_run(task, earliest_start_by_task):
        unschedulable.add(task, "predecessor_incomplete")
        continue

    earliest = max(now, earliest_start_by_task[pred_id] for pred_id in task.predecessor_ids if pred_id in earliest_start_by_task)
    member = find_member(task.assignee_id)
    windows = expand_working_windows(member, snapshot.project, [earliest, earliest+horizon])

    candidates = find_candidate_slots(task, windows, virtual_calendar_events)
    if not candidates:
        unschedulable.add(task, "no_capacity_before_deadline")
        continue

    candidates.sort(key=lambda s: -compute_fit_score(s, task, member))
    top_K = candidates[:options.max_candidates_per_task]

    selected = top_K[0]   # Agent의 추천
    slot_proposals.append(SlotProposal(task, top_K, selected_index=0))

    # 가상 점유 (다음 task 패킹에 영향)
    update_calendar_view(member, top_K[0])
    earliest_start_by_task[task.id] = top_K[0].ends_at

  proposals = repair_schedule_if_needed(proposals, snapshot, max_rounds=2)
  violations = validate_selected_schedule(proposals, snapshot)
  if violations:
      move_invalid_tasks_to_unschedulable(violations)
```

`priority_aware_topo_sort`는 위상 순서를 보장하면서 같은 indegree 0 후보끼리만 priority를 반영한다. `topo_sort()` 이후 전체 list를 다시 priority sort하면 선행/후행 순서가 깨질 수 있으므로 금지한다.

### 6.2 fit_score (결정적 가중합)

```python
def compute_fit_score(slot, task, member):
    # 0. 마감 여유 (가장 큰 신호)
    if task.deadline:
        slack = (task.deadline - slot.ends_at).total_seconds() / 3600  # 시간
        deadline_score = clamp(slack / 24, 0, 1)   # 24h 여유면 만점
    else:
        deadline_score = 0.5

    # 1. 근무가능시간 적합도
    in_window = is_within_working_window(slot, member)
    window_score = 1.0 if in_window else 0.2

    # 2. 담당자 부하 역수 (당일 이미 배정된 시간)
    same_day_hours = scheduled_hours_for_member_on_date(member, slot.starts_at.date())
    load_score = clamp(1 - (same_day_hours / 8), 0, 1)

    # 3. 프로젝트 시간대 몰림 감점
    density_penalty = project_density_penalty(slot, selected_slots)

    raw = 0.5 * deadline_score + 0.3 * window_score + 0.2 * load_score - density_penalty
    return round(raw * 100)
```

`project_density_penalty`는 같은 1시간 bucket에 이미 selected task가 많을수록 점수를 낮춘다. 목표는 모든 Task가 09:00 같은 동일 시작 시간에 몰리는 배치를 피하는 것이다.

### 6.3 quality 등급 (결정적 룰)

```
preferred:   in_window AND no hard_overlap AND deadline_score >= 0.5
acceptable:  in_window AND no hard_overlap AND deadline_score >= 0.0
fallback:    not in_window OR has hard_overlap OR deadline_score < 0
```

### 6.4 charlock 검사 (충돌)

```python
def detect_conflicts(slot, calendar_events):
    overlaps = []
    for e in calendar_events:
        if not (e.approved or e.source == "external_blocking"):
            continue
        if not interval_overlap(slot, e):
            continue
        # hard: 같은 담당자 동시 두 일정
        if e.assignee_id == slot.task.assignee_id:
            overlaps.append({"event_id": e.event_id, "kind": "hard_overlap"})
        else:
            overlaps.append({"event_id": e.event_id, "kind": "soft_overlap"})
    return overlaps
```

`hard_overlap`이 있는 슬롯은 quality=fallback 강제, fit_score -30 페널티.

### 6.5 실제 시간표 invariant

ScheduleResponse의 `selected_index`들이 가리키는 selected slots는 다음 invariant를 만족해야 한다.

1. `selected_index`가 `candidate_slots` 범위 안에 있다.
2. 같은 담당자의 selected slots끼리 시간이 겹치지 않는다.
3. task의 predecessor가 이번 response에 selected slot을 받았다면, predecessor selected slot의 `ends_at <= task selected slot.starts_at`이다.
4. selected slot은 task deadline을 넘지 않는다.
5. selected slot은 담당자 또는 프로젝트 working window 안에 있다.
6. selected slots 기준 동일 1시간 bucket에는 최대 2개 task까지만 허용한다.

6번은 quality invariant다. repair 후에도 deadline/capacity 때문에 피할 수 없는 경우에만 warning을 남기고 유지할 수 있다. LLM rerank가 6번을 깨면 전체 LLM rerank는 폐기한다.

### 6.6 제한적 repair

Greedy left-pack이 뒤 Task를 막거나 density invariant를 깨면 제한적 repair를 수행한다.

- repair 대상: 막힌 task의 predecessor chain + 같은 담당자의 이미 배치된 task
- 시도 범위: 각 대상 task의 2순위/3순위 candidate
- 최대 round: 2회
- 성공 조건: §6.5 invariant 통과
- 실패 처리: deterministic하게 원래 greedy 결과를 유지하거나, 해당 task를 `unschedulable`로 이동하고 reason을 남긴다.

이 repair는 global optimizer가 아니다. 전체 조합 최적화 대신 dependency와 same-assignee 충돌이라는 실제 실패 원인만 좁게 다룬다.

## 7. 워크플로우

```
┌─────────────────────────────────────────────────────────┐
│ Step 0: 입력 정합성                                       │
│   priority.tasks_priority가 snapshot.tasks와 정합        │
│   members 모두 weekly_capacity_hours, available_hours OK │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 1: Priority-aware 위상 정렬                          │
│   indegree 0 후보 중 priority 높은 Task부터 선택          │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 2: Task 순회 패킹                                    │
│   각 task에 대해 (a) 선행 완료 시점 (b) 근무 윈도우       │
│   (c) 충돌 (d) fit_score 계산                             │
│   → unschedulable에 사유 명시 또는 SlotProposal 생성      │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 3: 제한적 repair + final validation                  │
│   dependency chain + same-assignee 후보를 제한 재시도      │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 4: 가상 캘린더 갱신                                  │
│   다음 Task 패킹이 앞 결과를 반영                          │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Step 5: LLM Reranker (배치, 1 호출)                       │
│   입력: 모든 Task의 candidate_slots (결정적 floor 통과)   │
│   + Task title/description + project goal               │
│   출력: Task별 새 selected_index + 1문장 rationale        │
│   verify_rerank: index 순열 + final validation            │
│   위반 시 결정적 fit_score 순위로 fallback                │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
              결과 반환
```

## 8. unschedulable 사유 (전수)

원본 기획서 §4 "선행 Task 완료 전 후행 배치 방지" 등을 코드로 강제.

| reason | 의미 | UI 메시지 |
|---|---|---|
| `predecessor_incomplete` | 선행 Task가 이번 schedule run에서도 배치되지 못함 | "선행 Task 완료 또는 배치 가능 상태를 먼저 확인해 주세요" |
| `no_capacity_before_deadline` | 마감 전에 슬롯 못 찾음 | "마감 전 가능한 시간이 부족합니다" |
| `estimated_hours_missing` | 예상 소요시간 누락 | "예상 소요시간을 입력해 주세요" |
| `assignee_missing` | 담당자 미지정 | "담당자를 지정해 주세요" |
| `deadline_in_past` | 마감일이 과거 | "마감일이 지났습니다 — 마감 갱신이 필요합니다" |
| `circular_dependency` | DAG 순환 | Risk `dependency_correctness`가 blocker로 노출 |

## 9. 슬롯 분할 (task_blocks)

현재 MVP contract는 `task 하나 = selected slot 하나`다. 긴 Task도 여러 calendar event로 쪼개지 않고 `estimated_hours` 길이의 연속 slot을 찾는다.

`task_blocks()`는 분석/리포트 유틸로 유지한다. 4시간 블록 분할을 실제 `ScheduleResponse`에 반영하는 것은 FE 승인, calendar event, risk workload contract가 함께 바뀌는 다음 범위다.

```python
def task_blocks(task, options):
    total_min = int(task.estimated_hours * 60)
    max_block = options.maximum_block_minutes
    min_block = options.minimum_block_minutes
    blocks = []
    while total_min > 0:
        size = min(total_min, max_block)
        if size < min_block: size = min_block   # 마지막 작은 잔여 흡수
        blocks.append(size)
        total_min -= size
    return blocks
```

기본 `max_block=240` (4시간), `min_block=30`으로 6시간 Task → [240, 120]. 단, 이 결과는 현재 candidate slot 길이 결정에는 사용하지 않는다.

## 10. 가상 점유 (룩업 일관성)

같은 분석 호출 안에서, 앞 Task에 추천한 슬롯은 뒤 Task의 충돌 검사에 즉시 반영된다 — 단, **DB나 캘린더에 저장하지 않고 메모리 사본**에 마킹한다. PM이 G2에서 일부만 승인하면 미승인 슬롯은 사라진다.

## 10A. LLM Reranker (Step 4)

### 10A.1 의도

결정적 fit_score는 시간 산술과 충돌만 본다. 하지만 PM의 직관은 더 풍부하다:
- "리서치/설계" 류 Task → 오전 + 긴 연속 블록 선호
- "리뷰/회의 준비" Task → 회의 직전 1~2시간 선호
- "버그 수정" Task → 마감 임박이면 빠른 슬롯 선호
- 같은 마일스톤 Task끼리 같은 날에 묶이도록

LLM은 후보들을 보고 이런 패턴을 찾아 **순서만 바꾼다**.

### 10A.2 안전 floor 계약

LLM이 반환할 수 있는 것:
- Task별 `selected_index`의 새 값 (0..len-1)
- 후보들의 새 정렬 순서 (`ranked_indices`는 전체 후보 index의 정확한 순열)
- Task별 1문장 rationale (≤ 120자)

LLM이 반환할 수 없는 것 (verify_rerank가 차단):
- 새 datetime 필드
- 새 candidate_slot 추가
- candidate_slot 제거
- conflicts/fit_score 수정
- task_id 추가/제거
- selected schedule invariant 위반

### 10A.3 verify_rerank

```python
def verify_rerank(original: list[SlotProposal], payload: dict) -> list[str]:
    violations = []
    rerankings = payload.get("rerankings")
    if not isinstance(rerankings, list) or len(rerankings) != len(original):
        violations.append("rerank_shape_invalid")
        return violations

    for proposal in original:
        item = find_by_task_index_or_id(rerankings, proposal)
        if item is None:
            violations.append(f"rerank_violation:{proposal.task_id}")
            continue
        expected = list(range(len(proposal.candidate_slots)))
        ranked_indices = item.get("ranked_indices")
        selected_index = item.get("selected_index")
        if sorted(ranked_indices) != expected or selected_index != ranked_indices[0]:
            violations.append(f"rerank_violation:{proposal.task_id}")

    selected = apply_indices_without_mutating_slots(original, payload)
    violations.extend(validate_selected_schedule(selected))
    return violations
```

위반 시 **원본 결정적 결과를 그대로 사용** (LLM 결과 전체 폐기) + warning에 `rerank_violation:<task_id>` 또는 timeout reason 추가.

### 10A.4 LLM 호출 시점

- 분석할 Task가 0개면 호출 안 함
- 결정적 후보가 모두 quality=preferred이고 동수 1순위면 호출 안 함 (재정렬 효과 없음)
- 위 외에는 1회 호출 (배치, 모든 Task의 candidate_slots을 한 번에)

### 10A.5 latency / fallback

- LLM 호출 timeout 3s. 초과 시 결정적 결과로 fallback.
- 실패 1회 재시도 후에도 실패면 결정적 결과로 fallback. 둘 다 warning에 기록.

## 10B. LLM 프롬프트 (Reranker)

```
[SYSTEM]
You receive a batch of tasks, each with 1~5 candidate time slots that already
passed deterministic safety checks (no conflicts, within working hours,
predecessors complete). Your job: pick the BEST slot for each task by
reordering the candidates. Do NOT invent slots, modify datetimes, or
remove slots.

Consider these PM-style heuristics ONLY when supported by the task's
title/description:
- Research/design/writing tasks → prefer mornings or longer continuous blocks
- Review/meeting-prep tasks → prefer slots immediately before related meetings
- Bug-fix/operational tasks → prefer the earliest available slot
- Tasks of the same milestone → prefer same-day grouping when possible

For each task, output:
- ranked_indices: a permutation of original 0..N-1
- selected_index: ranked_indices[0]
- rationale: ONE Korean sentence ≤ 120 chars citing the task's title/desc
  AND the chosen slot's date/time. NO subjective judgments about people.

FORBIDDEN words: 매력, 호감, 인상, 성격, 게으, 느려, 의지, 무능, 책임감.

Output JSON only matching the schema.

[USER]
Project goal: <project.goal>
Milestones: <milestone names + due_dates>
Tasks with candidates: <list of {task_id, title, description, milestone, candidates[]}>
Schema: { "rerankings": [ { "task_id": "...", "ranked_indices": [..], "selected_index": int, "rationale": "..." } ] }
```

## 11. LangGraph Sub-graph 구조

### 11.0 ScheduleState

```python
class ScheduleState(BaseModel):
    snapshot: ProjectSnapshot
    priority: PriorityResponse
    horizon_days: int
    now: datetime
    options: ScheduleOptions

    # 산출물
    ordered_tasks: list[Task] = []
    slot_proposals: list[SlotProposal] = []     # 결정적 결과 (재정렬 전)
    reranked_proposals: list[SlotProposal] = [] # LLM 재정렬 후 (또는 fallback)
    rerank_rationales: dict[str, str] = {}      # task_id -> rationale
    rerank_violations: list[str] = []
    unschedulable: list[dict] = []
    warnings: list[str] = []
```

```python
def build_schedule_graph():
    g = StateGraph(ScheduleState)
    g.add_node("validate_inputs",   node_validate_inputs)
    g.add_node("topo_and_order",    node_topo_and_order)
    g.add_node("pack_tasks",        node_pack_tasks)
    g.add_node("llm_rerank",        node_llm_rerank)         # LLM
    g.add_node("verify_rerank",     node_verify_rerank)      # 결정적
    g.add_node("pack_response",     node_pack_response)

    g.set_entry_point("validate_inputs")
    g.add_edge("validate_inputs", "topo_and_order")
    g.add_edge("topo_and_order",  "pack_tasks")

    # 분기: 재정렬할 가치가 있는지
    g.add_conditional_edges(
        "pack_tasks",
        decide_should_rerank,
        {
            "rerank": "llm_rerank",
            "skip":   "pack_response",
        }
    )
    g.add_edge("llm_rerank",    "verify_rerank")

    # 분기: 검증 통과 시 reranked 사용, 실패 시 결정적 결과 사용
    g.add_conditional_edges(
        "verify_rerank",
        decide_after_verify,
        {
            "use_reranked":      "pack_response",
            "use_deterministic": "pack_response",
        }
    )
    g.add_edge("pack_response", END)
    return g.compile()

schedule_subgraph = build_schedule_graph()
```

### 11.0a 분기 함수

```python
def decide_should_rerank(state):
    if not state.slot_proposals:
        return "skip"
    if all(len(p.candidate_slots) == 1 for p in state.slot_proposals):
        return "skip"   # 재정렬 효과 없음
    return "rerank"

def decide_after_verify(state):
    if state.rerank_violations:
        state.warnings.extend(f"rerank_violation:{v}" for v in state.rerank_violations)
        return "use_deterministic"
    return "use_reranked"
```

### 11.1 노드 책임

| 노드 | 종류 | 책임 |
|---|---|---|
| `validate_inputs` | 결정적 | priority ↔ snapshot 정합성, member 필드 |
| `topo_and_order` | 결정적 | DAG 위상 정렬 + priority_score 보조 정렬 |
| `pack_tasks` | 결정적 | 메인 패킹 루프 (§6) → slot_proposals |
| `llm_rerank` | LLM (t=0) | 배치 재정렬 + rationale, timeout 3s + 재시도 1회 |
| `verify_rerank` | 결정적 | slot multiset/datetime/길이 검증, 위반 시 폐기 |
| `pack_response` | 결정적 | ScheduleResponse 패키징 (선택된 proposals + rationales) |

### 11.2 Super-graph 노출

```python
# backend/app/agents/schedule/__init__.py
from .graph import schedule_subgraph
__all__ = ["schedule_subgraph"]
```

## 12. 테스트 전략

### 12.1 단위 테스트
- `priority_aware_topo_sort`: 단일 체인 / 다중 ROOT / priority tie / 순환 안전망
- `expand_working_windows`: 평일/주말/제외일 / 요일별 다른 시간 / 다중 윈도우
- `task_blocks`: 1h / 4h / 6h / 0.25h(잔여) / 0h(유틸 결과)
- `compute_fit_score`: 마감 24h 전 / 1h 전 / 마감 후 / 윈도우 밖
- `detect_conflicts`: hard / soft / 인접 / 정확히 같은 시각 (오버랩 0)
- `validate_selected_schedule`: same-assignee overlap / dependency inversion / deadline exceed / working-window violation / 1시간 bucket 3개 이상
- `repair_schedule`: dependency chain + same-assignee 후보 교체, 최대 2 round

### 12.2 골든 시나리오 (5개)
1. 단순 3 Task 직선 의존 + 빈 캘린더 → preferred 슬롯 3개
2. 1명 담당자에 5 Task → 일부는 다음 주로 밀림 (preferred → acceptable)
3. 선행 미완료지만 이번 run에서 함께 배치 가능 → 선행 종료 후 후행 배치
4. 마감 1일 전 8h Task + 4h 캘린더 점유 → no_capacity
5. 다중 담당자 + 같은 시작 시간 3개 이상 후보 → repair 후 1시간 bucket 최대 2개로 분산

### 12.3 결정적 부분 결정성 테스트
- 동일 (snapshot, priority, now, horizon, options) 5회 호출 → `slot_proposals` (재정렬 전 결정적 결과) 100% 동일.
- LLM Reranker는 `temperature=0`이지만 모델 응답 변동 가능 → `reranked_proposals.selected_index`는 5회 중 4회 이상 동일 목표 (≥ 80%). 변동 시에도 verify_rerank가 항상 통과해야 함.

### 12.4 LLM Reranker 안전성 테스트
- LLM이 새 datetime 반환하도록 mock → schema/contract 차단 + fallback 동작 검증
- LLM이 슬롯 추가/제거 → 차단
- LLM이 task_id 누락 → 차단
- LLM이 `ranked_indices` 일부만 반환하거나 중복 반환 → 차단
- LLM이 selected schedule에 dependency inversion / hard overlap / density violation을 만들면 전체 rerank 폐기
- LLM이 금지 단어 사용 → 후처리 필터 차단 + fallback
- timeout 시 fallback 검증

### 12.5 통합 테스트
- 100 Task / 5 멤버 / 30일 horizon → 결정적 부분 ≤ 200ms, LLM 포함 P95 ≤ 3.5s

## 13. 성능 목표

| 지표 | 목표 |
|---|---|
| 결정적 후보 생성 latency (10 Task / 14일) | ≤ 50ms |
| 결정적 후보 생성 latency (100 Task / 30일) | ≤ 200ms |
| LLM Reranker latency P95 (배치 1회) | ≤ 3s |
| LLM 호출 수 | 1회/세션 (skip 조건 충족 시 0) |
| Slot validity (selected slot이 담당자 hard overlap 없음 + 윈도우 안 + 선행 후 + deadline 안) | 100% |
| Density quality (1시간 bucket selected task ≤ 2, 불가 시 warning) | ≥ 95% |
| Reranker safety (verify_rerank 위반 0건) | 100% |
| 결정적 부분 결정성 (5회 동일) | 100% |

## 14. 마일스톤

| 주차 | 산출물 |
|---|---|
| 1주차 | topo_sort + expand_working_windows + task_blocks + 단위 5개 |
| 2주차 | find_candidate_slots + compute_fit_score + detect_conflicts + 결정적 골든 5케이스 |
| 3주차 | 가상 점유 일관성 + LLM Reranker 노드 + verify_rerank + fallback 분기 + 100 Task 부하 테스트 |

## 15. 다른 역할과의 인터페이스

- **Priority Agent**: `tasks_priority[].score`만 사용. factors는 무시.
- **Risk Agent**: `slot_proposals`와 `unschedulable`을 입력으로 받아 deadline overrun, overload 검출.
- **Backend**: `schedule_subgraph` 단일 진입점. now 주입.
- **Frontend**:
  - candidate slots를 카드 리스트로 표시 (선택 가능)
  - quality에 따라 카드 색상 (preferred=초록, acceptable=노랑, fallback=주황)
  - unschedulable 영역은 빨간 배지 + reason 라벨
  - PM이 슬롯을 드래그해 시간 변경할 수 있음 → 변경된 시간이 G2 approve의 `override_starts_at`로 전달

## 16. 정직성 노트

- 본 Agent는 **결정적 floor + LLM Reranker** 하이브리드다. 시간 산술과 충돌 검사는 코드가, 의미·맥락 기반 정렬은 LLM이 한다.
- LLM이 폭주해도 결정적 floor가 안전망 — verify_rerank가 위반을 잡으면 결정적 결과로 fallback. **사용자가 받는 슬롯은 항상 안전한 슬롯이다.**
- fit_score 가중치(0.5/0.3/0.2)는 **튜닝하지 않는다**. 골든 셋이 이상하면 가중치 대신 입력(estimated_hours, working_hours)을 의심한다.
- LLM Reranker가 가치 없는 경우(후보 1개씩, 모두 동일 quality)에는 호출 자체를 skip한다 — 비용 절감 + fallback 케이스 감소.
