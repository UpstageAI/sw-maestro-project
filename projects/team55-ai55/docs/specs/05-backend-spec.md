# 05. Backend — 사양

> 담당자: Backend 개발자 1명
> 책임: API Gateway / DTO 검증 / Agent 오케스트레이션 / 캐싱 / 관측성 / Upstage API 키 관리

## 1. 책임

1. REST API 제공 (Frontend ↔ Backend 경계)
2. ProjectSnapshot 입력 검증, 정규화 (now 주입, ID 발급)
3. 3개 Agent의 오케스트레이션 (super-graph)
4. snapshot_hash 단위 캐싱 (멱등성)
5. 외부 의존성 (Upstage API) 키 관리 + rate limit
6. 관측성: 로깅, 메트릭, 트레이싱
7. **G1/G2 승인 게이트 강제** — 승인 없는 캘린더 INSERT 거부

## 2. 비-책임

| 항목 | 책임자 |
|---|---|
| Task 분해 / 우선순위 점수 | Priority Agent 담당자 |
| 슬롯 후보 생성 | Schedule Agent 담당자 |
| 리스크 체크 평가 | Risk Agent 담당자 |
| UI 렌더링 / localStorage | Frontend 담당자 |
| 영속 DB 운영 | (없음 — 본 MVP는 무서버 영속, FE localStorage만) |

Backend는 위 모듈을 **호출**하고 게이트를 **강제**할 뿐, 내부 로직은 담당자별 모듈에 위임.

## 3. 기술 스택

- 언어: Python 3.11+
- 프레임워크: FastAPI (원본 기획서 §4 명시 — `fastapi`)
- **오케스트레이션: LangGraph 0.2+** (각 Agent는 sub-graph, Backend는 super-graph)
- LLM 클라이언트: Upstage API SDK (또는 OpenAI-호환 endpoint를 직접 httpx로)
- 비동기: `asyncio`, `httpx`
- 검증: Pydantic v2
- 관측성: LangSmith trace (선택, 환경변수)
- 테스트: pytest, pytest-asyncio
- 로깅: structlog (JSON 로깅)
- 캐시: in-memory dict (MVP 단일 프로세스) → 스케일 아웃 시 Redis로 전환

## 4. API 엔드포인트

상세 schema는 `07-data-contracts.md §6`. 본 절은 라우터-레벨 책임 위주.

| 메서드 | 경로 | 책임 | LLM 호출 |
|---|---|---|---|
| POST | `/v1/projects` | 프로젝트 생성 (저장 안 함, project_id만 발급) | 0 |
| POST | `/v1/projects/{id}/milestones:suggest` | 마일스톤 후보 LLM 호출 | 1 |
| POST | `/v1/projects/{id}/milestones:approve` | G1 게이트 통과 → 승인된 마일스톤 반환 | 0 |
| POST | `/v1/projects/{id}/analyze` | super-graph 호출 (priority + schedule + risk) | 평균 4 (Priority Narrator 1 + Schedule Reranker 1 + Risk Soft Checks 1 + Risk Narrator 1, 분해 요청 시 +N) |
| POST | `/v1/projects/{id}/schedule:approve` | G2 게이트 + 캘린더 이벤트 변환 | 0 |
| POST | `/v1/projects/{id}/risk:simulate` | risk_subgraph hard lane 재실행 (LLM 미사용) | 0 |
| GET  | `/v1/health` | upstage_api 헬스 체크 | 0 |

### 4.1 Stateless 원칙

서버는 영속 저장소가 없다 (MVP). 모든 요청은 `snapshot`을 본문에 받고, 응답으로 추천만 반환한다. **이것은 원본 기획서 167~177행의 시스템 워크플로우 결정과 일치한다**:
- 프론트엔드 → localStorage 저장
- 프론트엔드 → snapshot을 FastAPI에 전달
- FastAPI → AI 응답 검증 후 반환
- 프론트엔드 → 승인 후 localStorage 갱신

## 5. 오케스트레이션 (LangGraph Super-graph)

### 5.1 SessionState

```python
from typing import Optional
from pydantic import BaseModel

class SessionState(BaseModel):
    # 입력
    project_id: str
    snapshot: ProjectSnapshot
    options: AnalyzeOptions
    now: datetime           # Backend가 주입 (결정성 + 테스트)

    # snapshot_hash (멱등 키)
    snapshot_hash: str

    # Agent sub-graph 산출물
    priority: Optional[PriorityResponse] = None
    schedule: Optional[ScheduleResponse] = None
    risk:     Optional[RiskResponse] = None

    # 메타
    agent_latencies_ms: dict = {}
    cache_hit: bool = False
    llm_calls_total: int = 0
    errors: list[dict] = []
```

### 5.2 Super-graph 정의

```python
from langgraph.graph import StateGraph, END
from app.agents.priority import priority_subgraph    # compiled sub-graph
from app.agents.schedule import schedule_subgraph
from app.agents.risk     import risk_subgraph

def build_super_graph():
    g = StateGraph(SessionState)

    g.add_node("normalize",       normalize_node)         # 결정적 (now 주입, ID 발급, hash)
    g.add_node("priority",        priority_subgraph)      # Agent sub-graph
    g.add_node("schedule",        schedule_subgraph)      # Agent sub-graph
    g.add_node("risk",            risk_subgraph)          # Agent sub-graph
    g.add_node("pack_response",   pack_response_node)     # 결정적

    g.set_entry_point("normalize")

    # priority 먼저 (점수 → schedule + risk가 사용)
    g.add_edge("normalize", "priority")

    # priority 후 schedule + risk 병렬
    g.add_edge("priority", "schedule")
    g.add_edge("priority", "risk")

    # join: 둘 다 끝나야 pack
    g.add_edge(["schedule", "risk"], "pack_response")

    g.add_edge("pack_response", END)
    return g.compile()

SUPER_GRAPH = build_super_graph()
```

### 5.3 FastAPI 라우터 호출 패턴

```python
@router.post("/v1/projects/{project_id}/analyze")
async def analyze(project_id: str, req: AnalyzeRequest, now: datetime = Depends(get_now)):
    snapshot_hash = compute_snapshot_hash(req.snapshot)
    cached = await cache.get(("analyze", project_id, snapshot_hash))
    if cached:
        return cached.with_meta(cache_hit=True)

    state = SessionState(
        project_id=project_id,
        snapshot=req.snapshot,
        options=req.options,
        now=now,
        snapshot_hash=snapshot_hash,
    )
    final = await SUPER_GRAPH.ainvoke(state)
    response = final.to_response()
    await cache.put(("analyze", project_id, snapshot_hash), response, ttl=3600)
    return response
```

### 5.4 Backend가 직접 책임지는 노드

| 노드 | 종류 | 책임 |
|---|---|---|
| `normalize` | 결정적 | now 주입, snapshot_hash 계산, 누락 default 채움 (`weekly_capacity_hours=40`) |
| `pack_response` | 결정적 | SessionState → AnalyzeResponse 변환, latency/llm_calls 집계 |

Agent sub-graph(`priority_subgraph`, `schedule_subgraph`, `risk_subgraph`)의 내부 노드는 **각 Agent 담당자가 자체 spec(02/03/04)에 따라 정의**한다. Backend는 sub-graph의 입출력 schema만 알면 된다.

### 5.5 에러 전파

- 각 sub-graph는 실패 시 `state.errors` 에 항목 추가하고 다음 노드로 진행하거나, fatal 에러는 예외로 전파.
- super-graph 차원에서 fatal 예외는 FastAPI 에러 핸들러가 HTTP 코드로 변환 (`07-data-contracts.md §6.8`).
- 부분 실패 (예: schedule이 일부 task만 unschedulable)는 errors가 아니라 정상 응답의 unschedulable 필드에 기록.

### 5.6 LangSmith 통합 (선택)

환경변수로 제어:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=ai-swm-55
```
활성화 시 모든 노드 입출력, latency, token이 자동 기록되며, `project_id::snapshot_hash`가 trace ID로 연결된다.

## 6. snapshot_hash 계산 (결정성)

```python
def compute_snapshot_hash(snapshot: ProjectSnapshot) -> str:
    canonical = json.dumps(snapshot.model_dump(mode="json"),
                           sort_keys=True, separators=(",", ":"),
                           default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
```

- 모든 ID는 발급 후 고정 → hash 안정.
- timestamp 정밀도는 초 단위로 표준화 (마이크로초 무시) — 클라이언트 시계 흔들림 흡수.

## 7. G2 게이트 — 캘린더 승인

```python
@router.post("/v1/projects/{project_id}/schedule:approve")
async def approve_schedule(project_id: str, req: ApproveScheduleRequest):
    cached = await cache.get(("analyze", project_id, req.snapshot_hash))
    if cached is None:
        raise HTTPException(409, code="snapshot_hash_stale",
                            message="분석 결과가 만료되었습니다. 재분석 후 다시 승인해주세요.")
    schedule = cached.schedule

    events_created = []
    events_rejected = []
    for approval in req.approvals:
        proposal = next((p for p in schedule.slot_proposals
                         if p.task_id == approval.task_id), None)
        if proposal is None:
            events_rejected.append({"task_id": approval.task_id, "reason": "task_not_found"})
            continue

        idx = approval.candidate_slot_index
        if not (0 <= idx < len(proposal.candidate_slots)):
            events_rejected.append({"task_id": approval.task_id, "reason": "candidate_index_out_of_range"})
            continue

        slot = proposal.candidate_slots[idx]
        starts_at = approval.override_starts_at or slot.starts_at
        ends_at   = approval.override_ends_at   or slot.ends_at
        # 오버라이드한 슬롯도 충돌 검사 1회 (안전장치)
        if has_hard_overlap(starts_at, ends_at, project_id, approval.task_id, request_calendar=cached.snapshot.calendar_events):
            events_rejected.append({"task_id": approval.task_id, "reason": "override_conflicts"})
            continue

        events_created.append(InternalCalendarEvent(
            event_id=mint_event_id(),
            project_id=project_id,
            task_id=approval.task_id,
            assignee_id=task_of(approval.task_id).assignee_id,
            starts_at=starts_at,
            ends_at=ends_at,
            approved=True,
            approved_at=now(),
            source="ai_suggested",
        ))

    return {"events_created": events_created, "events_rejected": events_rejected}
```

**Backend의 G2 게이트 보장:**
- snapshot_hash가 만료되면 승인 거부 (409)
- 후보 인덱스 범위 검증
- override 슬롯도 hard_overlap 검사 (안전장치)
- 캘린더 INSERT 자체는 Frontend가 응답을 받아 localStorage에 저장 (서버 영속 없음). Backend는 events_created 리스트를 **반환만** 한다.

## 8. 캐싱

| 데이터 | 키 | TTL | 저장소 |
|---|---|---|---|
| analyze 응답 | `analyze:{project_id}:{snapshot_hash}` | 1h | in-memory |
| milestones:suggest | `milestones:{project_id}:{goal_hash}` | 24h | in-memory |
| 헬스체크 | `health:upstage` | 30s | in-memory |

MVP는 단일 프로세스 가정. 다중 인스턴스 시 Redis로 교체 (인터페이스 동일).

## 9. Rate Limiting

- IP 기준: 30 req/min
- 글로벌: Upstage API 동시 호출 큐 (max concurrency 5)
- LLM 일일 한도 (env: `LLM_DAILY_BUDGET`, default 500). 초과 시 분해/Narrator는 fallback 룰만 동작.

## 10. 관측성

### 10.1 구조적 로깅
```json
{
  "ts": "...",
  "level": "info",
  "event": "agent_call",
  "project_id": "...",
  "snapshot_hash": "...",
  "agent": "priority|schedule|risk|super",
  "latency_ms": 1234,
  "tokens_in": 1024,
  "tokens_out": 512,
  "schema_pass": true,
  "retry_count": 0,
  "cache_hit": false
}
```

### 10.2 메트릭 (Prometheus 권장)
- `agent_latency_seconds{agent}`
- `agent_failures_total{agent, reason}`
- `schema_pass_rate{agent}`
- `llm_calls_total{purpose}` (decompose / narrate_priority / narrate_risk / suggest_milestone)
- `policy_violation_total{filter}` (금지 단어 감지)

### 10.3 트레이싱
- `project_id::snapshot_hash`를 trace ID로 사용
- Agent 호출은 child span

## 11. 보안

- API 키는 환경변수 (`UPSTAGE_API_KEY`)
- CORS: Frontend origin만 허용
- 로그에 raw LLM prompt 저장 금지 (Task 본문에 PII가 있을 수 있음 — 7일 후 자동 삭제)
- 본 MVP는 인증 없음 — 프로토타입이므로 외부 망 노출 시 reverse proxy로 인증 추가 권장

## 12. 테스트 전략

### 12.1 단위 테스트
- 라우터별 입력 검증 (validation_error 케이스)
- snapshot_hash 안정성 (필드 순서 무관)
- G2 게이트: stale hash, out_of_range, override_conflicts, 정상

### 12.2 통합 테스트
- super-graph: mock된 sub-graph로 시퀀스 검증
- 캐시 hit / miss 검증
- LangSmith 환경변수 ON/OFF

### 12.3 E2E (CI gating)
- 골든 snapshot → analyze → schedule:approve → events_created 검증
- 실제 Upstage API 호출 (CI default mocked, nightly real)
- 5개 시나리오 (08-roles-and-handoffs §7)

## 13. 성능 목표

| 지표 | 목표 |
|---|---|
| Latency P50 (cold analyze) | ≤ 5s (LLM 4회 일부 병렬) |
| Latency P95 (cold analyze) | ≤ 7s |
| Latency P50 (cache hit) | ≤ 100ms |
| schedule:approve | ≤ 200ms |
| risk:simulate (hard lane only) | ≤ 200ms |
| 동시 요청 처리 | ≥ 5 req 동시 |
| 메모리 사용량 | ≤ 500MB |

## 14. 마일스톤

| 주차 | 산출물 |
|---|---|
| 1주차 | FastAPI 스캐폴드 + projects/milestones:suggest + Upstage 클라이언트 + LangGraph 골격 |
| 2주차 | analyze 라우터 + super-graph 골격(stub sub-graph) + snapshot_hash + 캐시 |
| 3주차 | schedule:approve G2 게이트 + risk:simulate + 관측성 + E2E 5개 |

## 15. 다른 역할과의 인터페이스

- **Frontend**: API 계약(`07-data-contracts.md`)을 단일 진실 소스로 사용. OpenAPI schema 자동 생성/배포(`/openapi.json`).
- **Priority/Schedule/Risk Agent 담당자**: 각 모듈의 `*_subgraph` 객체가 본 spec의 import 경로(`app.agents.{name}`)와 일치하도록 협의.
- **CODEOWNERS**: 본 spec과 라우터는 backend-owner 단독, super-graph 노드는 backend + agent owner 양 리뷰.

## 16. 정직성 노트

- Backend는 본 프로젝트에서 **얇다**. DB가 없고, 인증도 없고, 알림도 없다.
- 두꺼워야 하는 부분은 **G2 게이트의 안전성** 하나뿐 — 승인되지 않은 어떤 슬롯도 events_created에 들어가면 안 된다.
- Stateless 결정은 원본 기획서의 localStorage 기반 영속화와 정합한다. 사용자 데이터 사라짐 위험은 Frontend의 export/import 기능으로 보완한다.
