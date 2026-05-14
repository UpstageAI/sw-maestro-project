# ADR-0012: 관측성 — LangSmith trace + 호스팅 기본 로그

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

ADR-0010(데이터 모델), ADR-0011(호스팅), ADR-0005 부록(LangGraph 토폴로지) 결정 후 운영·디버그를 위한 관측성 도구 선택 필요. 비영리 사이드 + 데모/지인 단위 사용 가정 → 무료 한도 + 자동 과금 회피가 핵심 요구.

## Decision

| 영역 | 선택 |
|---|---|
| LLM trace | **LangSmith Developer (Free)** — 카드 미등록 |
| 에러 모니터링 | **Vercel / Railway 기본 로그** — 별도 SaaS 없음 |
| 사용자 사용량 | **Supabase 직접 query + LangSmith** — 별도 도구 없음 |
| Trace 컨벤션 | `session_id` / `seq` metadata + `owner_id_hash` (PII 회피) |

## Rationale

### LangSmith 선택
- LangGraph 자동 통합 — 환경변수 1개(`LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`)로 모든 노드 step 자동 trace.
- **카드 미등록 = 자동 과금 발생 0**. Free 5,000 trace/월 도달 시 trace 전송만 차단, 서비스 자체엔 부수효과 없음.
- 우리 use case 계산: 사용자당 일일 8회 × 30일 = 240 trace → **Free 한도 안에서 약 20명 풀 사용 가능** (데모/지인 단위 충분).
- LangChain/LangGraph 생태와 정합 → 평가셋·prompt 회귀 테스트 도구도 같은 dashboard에서.

### 호스팅 기본 로그 선택
- Vercel(Functions logs) + Railway(Service logs) 기본 제공, 무료, 검색 가능.
- Sentry는 트래픽 늘었을 때 별도 ADR로 도입.
- MVP 운영자(=개발자 본인)가 dashboard 둘만 보면 충분.

### 별도 사용량 도구 없음
- 일일 카운트 = `usage_quotas` SELECT.
- 실패율 = LangSmith trace의 error 필터.
- 사용자 행동 분석은 MVP 외.

## Trace 컨벤션

```python
# Gateway에서 LangGraph 호출 시
graph.ainvoke(
    state,
    config={
        "metadata": {
            "session_id": state["session_id"],
            "seq": state["seq"],
            "owner_id_hash": sha256(state["owner_id"])[:16],  # PII 직접 노출 회피
            "species_normalized": normalize_species(state["species"]),
        },
        "tags": [f"seq={state['seq']}", state["species_normalized"]],
    }
)
```

- `safety_violation` 발생 시 LangGraph 노드 출력으로 자동 trace에 기록 → tag로 회귀 분석.
- prompt/response 본문은 자동 capture (LangSmith default) — 일기 본문은 PII 가능성 약하나 외부 SaaS 송출이라는 점은 인지하고 채택.
- `owner_id`는 그대로 보내지 않고 hash 16자만 — 사용자별 trace 추적은 가능하면서 user-id 자체는 LangSmith에 노출되지 않음.

## Alternatives Considered

- **Langfuse self-host** — 인프라 1개 추가 부담 (DB + container). 비영리 사이드에 과함.
- **Langfuse Cloud** — Free 50k events/월로 한도는 큼, but LangChain 자동 통합 시 LangSmith 우위.
- **자체 로깅 (Supabase INSERT)** — dashboard 자체 작성 부담 큼. 가치 대비 비용 큼.
- **Sentry** — error tracking 강력하지만 trace는 약함. 트래픽 증가 후 별도 도입.
- **OpenAI Dashboard logs** — request 단위만, LangGraph 노드 step 분해 X.
- **관측성 도구 X** — 디버그 시 BFF 로그만으론 LangGraph 내부 추적 어려움. Free 옵션 있는데 굳이 포기할 이유 없음.

## Consequences

### Pros
- 환경변수 1개로 모든 LangGraph 노드 자동 trace.
- 카드 미등록 → 자동 과금 절대 발생 X.
- 데모/지인 단위 사용에 무료 한도 충분.

### Cons
- prompt/일기 본문이 외부 SaaS(LangSmith)로 송출 — PII 가능성 인지하고 채택.
- 한도 도달 시 trace 전송만 차단 → 그 시점에 운영자가 인지하고 카드 등록 또는 한도 절약(`LANGSMITH_TRACING=false` toggle).
- 에러 추적 dashboard 통합 부족 — Vercel/Railway/LangSmith 셋을 따로 봐야 함.

### 후속 조치 (사용자 액션, GUI)
- `smith.langchain.com` 가입 (GitHub OAuth) — **카드 등록 안 함**.
- API key 생성 → BFF/Gateway 환경변수 입력.
- (트래픽 늘어 5k 도달 시) 카드 등록 결정 또는 trace toggle off.

### 후속 조치 (코드)
- Gateway `call_llm` 노드에서 LangSmith metadata/tag 채우기.
- BFF Route Handler에서 5xx 발생 시 Vercel logs에 구조화된 JSON 로그 (level, route, owner_id_hash, error).
- Railway service에서 uvicorn access log 활성화.
