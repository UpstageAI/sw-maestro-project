# autocoin-ai · 다운스트림 영향 (FE / BE)

> **상태**: 캐노니컬
> **작성일**: 2026-05-10
> **연관 저장소**: `autocoin-api` (BE), `autocoin-web` (FE)
> **읽는 사람**: BE/FE 담당자, 평가자

이 문서는 `autocoin-ai`의 Agentic Upgrade가 **다른 두 저장소(BE/FE)에 미치는 영향**을 정리한다.
**MVP에서는 BE/FE 변경 없음**. Phase 2(후속)에서 통합 시 필요한 사양만 사전 정의.

---

## §1. 핵심 요약

| 시점 | autocoin-api (BE) | autocoin-web (FE) |
|---|---|---|
| **MVP (이번 제출)** | **변경 없음** | **변경 없음** |
| **Phase 2 (후속)** | 5개 tool proxy + 라우팅 1개 + 사용자 계정 1 필드 | 챗 UI + 진행 표시 + trace 시각화 |

---

## §2. MVP — 왜 BE/FE 변경 없는가

### 2.1 격리 원칙
새 Agentic 흐름은 **AI 저장소 안에서 자급자족**:
- 자연어 입력은 `examples/*.json`의 `request_context.user_input.text` 필드로 직접 받음
- BE의 도구는 `tools/_mock_data.py`의 fixture로 대체
- FE는 CLI 데모로 대체 (`python -m autocoin_ai.cli run examples/<scenario>.json`)
- 영상 녹화로 시연

### 2.2 기존 BE/FE 호환성
새 흐름은 **기존 흐름을 깨지 않음**:
- `request_context.user_input`이 기존 dict (`{symbol, side, type, ...}`) 형태면 → intake 노드의 dict 모드로 처리
- `request_context.user_input.text`가 있으면 → 새 LLM 파싱 모드
- 둘 다 같은 `normalized_order_intent`로 합류 → 이후 흐름 동일

→ BE가 기존처럼 dict 보내든, 새로 text 보내든 AI는 둘 다 받음.

### 2.3 평가 시점에 보일 것
평가자는 코드만 봄:
- `autocoin-ai` 저장소 단일 → 이 안의 코드 + 테스트 + examples + README + 영상
- BE/FE 변경 없으므로 다른 저장소를 봐달라고 요청할 필요 없음

---

## §3. Phase 2 — autocoin-api (BE) 변경 사양

> **이 절은 "후속 작업 명세"임. 이번 제출 범위 X.**

### 3.1 변경 1 — `request_context.user_input.text` 라우팅

**현재**: BE는 FE에서 받은 dict를 그대로 AI에 전달.
**Phase 2**: `text` 필드 있으면 그대로 통과 + `persona_default` 박기.

```python
# autocoin-api/app/routes/orders.py (예상)
@router.post("/orders/test")
async def submit_order_test(req: OrderTestRequest, user: User = Depends(...)):
    ai_payload = {
        "run_id": generate_run_id(),
        "request_context": {
            "request_id": req.request_id,
            "request_type": "PLACE_ORDER_TEST",
            "requested_at": datetime.utcnow().isoformat() + "+09:00",
            "user_input": {
                **req.user_input.dict(),
                "persona_default": user.persona_default,  # 🆕 사용자 계정 디폴트
                "market_snapshot": await fetch_market_snapshot(req.symbol),  # 🆕 BE가 미리 패키징
            },
        },
        "policy_context": await retrieve_policy_context(req),
    }
    return await ai_client.start_run(ai_payload)
```

**난이도**: ⭐ (한 줄 추가 수준)

### 3.2 변경 2 — Market Snapshot 사전 패키징 (신규 함수)

**목적**: AI가 Binance Testnet 직접 호출 못 하므로 BE가 시장 스냅샷을 미리 박아야 함.

```python
# autocoin-api/app/services/market.py
async def fetch_market_snapshot(symbol: str) -> dict:
    """주문 직전 시장 상태를 dict로 패키징.
    AI가 strategy 노드에서 의사결정 근거로 사용."""
    ticker = await binance_testnet.get_ticker(symbol)
    return {
        "symbol": symbol,
        "price_usd": ticker.last_price,
        "trend": classify_trend(ticker),  # "UP" | "DOWN" | "SIDEWAYS"
        "volume_24h": ticker.volume,
        "fetched_at": datetime.utcnow().isoformat() + "+09:00",
    }
```

**난이도**: ⭐⭐ (신규 함수 + Binance API 호출)

### 3.3 변경 3 — 사용자 계정에 `persona_default` 필드 (DB 마이그레이션)

```sql
ALTER TABLE users ADD COLUMN persona_default VARCHAR(20) DEFAULT 'MODERATE';
-- 값: CONSERVATIVE | MODERATE | AGGRESSIVE
```

```python
# autocoin-api/app/models/user.py
class User(BaseModel):
    id: int
    email: str
    persona_default: Literal["CONSERVATIVE", "MODERATE", "AGGRESSIVE"] = "MODERATE"  # 🆕
```

**난이도**: ⭐⭐ (마이그레이션 + 모델 + UI 연동)

### 3.4 변경 4 — Tool Proxy Endpoints 5개 (신규)

**목적**: AI의 risk_gate / risk_agent가 호출할 BE 도구 endpoint.
**원칙**: AI는 Binance를 직접 호출하지 않음. BE가 proxy.

| Endpoint | Method | Body | 응답 |
|---|---|---|---|
| `/tools/account/balance` | POST | `{asset, run_id}` | `{free, locked, total}` |
| `/tools/market/volatility` | POST | `{symbol, days, run_id}` | `{atr_pct, stdev_pct, window_days}` |
| `/tools/account/concentration` | POST | `{symbol, proposed_size_usd, run_id}` | `{current_pct, after_pct}` |
| `/tools/policy/persona-bounds` | POST | `{action, symbol, size_usd, run_id}` | `{allowed: bool, reason}` |
| `/tools/calendar/economic` | POST | `{hours_ahead, run_id}` | `{events: [...]}` |

**인증/보안**:
- `run_id` 화이트리스트: BE는 활성 run_id만 도구 호출 허용
- 호출 캐싱: 같은 `(run_id, tool, args)`은 캐시 (TTL 60초)
- Rate limit: 한 run당 도구 총 호출 수 제한 (advisor MAX_TOOL_CALLS와 일치, 4)

**구현 예시**:
```python
# autocoin-api/app/routes/tools.py
@router.post("/tools/market/volatility")
async def get_volatility_proxy(req: VolatilityRequest):
    if not is_active_run(req.run_id):
        raise HTTPException(403, "run_id not active")
    cache_key = ("volatility", req.symbol, req.days)
    if cached := tool_cache.get(req.run_id, cache_key):
        return cached
    klines = await binance_testnet.get_klines(req.symbol, "1d", req.days + 1)
    result = compute_volatility(klines)
    tool_cache.set(req.run_id, cache_key, result, ttl=60)
    return result
```

**난이도**: ⭐⭐⭐ (5개 endpoint + 캐싱 + 인증)

### 3.5 변경 5 — AI 응답에 새 필드 노출

BE의 `OrderTestResponse` 스키마 확장:

```python
class OrderTestResponse(BaseModel):
    run_id: str
    lifecycle_status: str
    hold_reason: Optional[str]
    decision_trace: dict
    verification_checks: list

    # 🆕 Agentic 추가
    inferred_persona: str
    persona_override_reason: Optional[str]
    trader_id: str
    llm_proposal: dict
    risk_assessment: dict
    risk_tool_calls: list
    evaluator_review: dict
```

**난이도**: ⭐ (필드 추가만)

### 3.6 BE 변경 합산

| 변경 | 난이도 | 예상 시간 |
|---|---|---|
| `text` 라우팅 | ⭐ | 30분 |
| Market snapshot | ⭐⭐ | 2h |
| persona_default DB | ⭐⭐ | 1.5h |
| 도구 proxy 5개 | ⭐⭐⭐ | 6h |
| AI 응답 필드 노출 | ⭐ | 30분 |
| **합계** | - | **~10h** |

---

## §4. Phase 2 — autocoin-web (FE) 변경 사양

### 4.1 변경 1 — 챗 입력 UI (신규)

**현재**: 폼 기반 (symbol, side, type, qty 입력).
**Phase 2**: 텍스트 인풋 + 빠른 예시 버튼.

```tsx
// autocoin-web/src/features/order-test/ChatInput.tsx
function ChatInput() {
  const [text, setText] = useState("");
  const examples = [
    "BTC 5만원 사줘",
    "공격적으로 ETH 10만원 매수",
    "리버모어 스타일로 BTCUSDT 100 USDT",
  ];
  return (
    <div>
      <textarea value={text} onChange={e => setText(e.target.value)} />
      <div>
        {examples.map(ex => <button onClick={() => setText(ex)}>{ex}</button>)}
      </div>
      <button onClick={() => submit({ text })}>주문 테스트 시작</button>
    </div>
  );
}
```

**호환성**: 기존 폼 UI 유지. 챗 UI는 별도 탭 또는 토글.

**난이도**: ⭐⭐

### 4.2 변경 2 — Persona 프로필 화면 (신규)

```tsx
// autocoin-web/src/features/account/PersonaProfile.tsx
function PersonaProfile() {
  const personas = [
    { id: "CONSERVATIVE", label: "🛡 보수형", maxOrder: "$100", symbols: ["BTC", "ETH"] },
    { id: "MODERATE",     label: "⚖️ 중립형", maxOrder: "$500", symbols: ["BTC, ETH, SOL"] },
    { id: "AGGRESSIVE",   label: "🚀 공격형", maxOrder: "$2000", symbols: ["BTC, ETH, SOL, ..."] },
  ];
  // 각 persona 카드 + 현재 선택 표시 + 변경 버튼
}
```

**난이도**: ⭐⭐

### 4.3 변경 3 — AI 진행 스트리밍 (SSE)

**목적**: AI 노드 진행 상황을 실시간 표시.

```tsx
// autocoin-web/src/features/order-test/ProgressStream.tsx
function ProgressStream({ runId }: { runId: string }) {
  const [stages, setStages] = useState<StageEvent[]>([]);
  useEffect(() => {
    const sse = new EventSource(`/api/runs/${runId}/stream`);
    sse.onmessage = (e) => setStages(prev => [...prev, JSON.parse(e.data)]);
    return () => sse.close();
  }, [runId]);
  return (
    <div>
      {stages.map(s => (
        <StageRow key={s.stage} stage={s.stage} status={s.status} />
      ))}
    </div>
  );
}
```

**BE 의존**: BE에 SSE endpoint 추가 필요.

**난이도**: ⭐⭐⭐

### 4.4 변경 4 — Decision Trace + Tool Calls 시각화

```tsx
function DecisionTraceView({ trace, toolCalls }: Props) {
  return (
    <div>
      {/* stage별 패널 */}
      <StagePanel stage="intake"   data={trace.intake} />
      <StagePanel stage="policy"   data={trace.policy} />
      <StagePanel stage="strategy" data={trace.strategy} />
      <StagePanel stage="risk"     data={trace.risk} />
        {/* 도구 호출 타임라인 */}
        <ToolCallTimeline calls={toolCalls} />
      <StagePanel stage="evaluator" data={trace.evaluator} />
    </div>
  );
}
```

**난이도**: ⭐⭐⭐

### 4.5 변경 5 — HOLD/Resume UX

HOLD 사유별 안내 + 보완 입력 폼.

```tsx
function HoldRecoveryFlow({ run }: { run: AgentRun }) {
  if (run.hold_reason === "HOLD_INPUT_AMBIGUOUS") {
    return <ClarificationPrompt run={run} />;
  }
  if (run.hold_reason === "HOLD_LOW_CONVICTION") {
    return <LowConvictionExplanation run={run} />;
  }
  // ...
}
```

**Phase 2 후속**: resume 자체를 BE/AI에서 지원해야 함 (CONTRACTS §9 참조 — MVP는 미지원).

**난이도**: ⭐⭐ (UI만)

### 4.6 FE 변경 합산

| 변경 | 난이도 | 예상 시간 |
|---|---|---|
| 챗 입력 UI | ⭐⭐ | 4h |
| Persona 프로필 | ⭐⭐ | 4h |
| 진행 스트리밍 (SSE) | ⭐⭐⭐ | 8h |
| Trace + Tool 시각화 | ⭐⭐⭐ | 10h |
| HOLD/Resume UX | ⭐⭐ | 4h |
| **합계** | - | **~30h** |

---

## §5. 인터페이스 계약 변경

### 5.1 FE → BE 요청 (`POST /orders/test`)

```jsonc
// 기존 (호환 유지)
{
  "user_input": {
    "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quoteOrderQty": "50"
  }
}

// 신규 (Phase 2)
{
  "user_input": {
    "text": "BTC 5만원치 사줘",            // 🆕 자연어 (있으면 우선)
    "trader_id": "wonyotti"                // 🆕 사용자가 명시적으로 트레이더 선택
  }
}
```

### 5.2 BE → AI 요청 (`POST {AI_URL}/runs/start`)

기존과 동일. 단지 `request_context.user_input` 필드가 다양해짐:
```jsonc
{
  "run_id": "...",
  "request_context": {
    "user_input": {
      "text": "BTC 5만원치 사줘",
      "trader_id": "wonyotti",
      "persona_default": "MODERATE",        // 🆕 BE가 사용자 계정에서
      "market_snapshot": {...}              // 🆕 BE가 사전 패키징
    }
  },
  "policy_context": {...}
}
```

### 5.3 AI → BE 응답

기존 응답 + 신규 필드 (CONTRACTS §13.2):
```jsonc
{
  "run_id": "...",
  "lifecycle_status": "READY_FOR_BE",
  "decision_trace": {...},
  "verification_checks": [...],

  "trader_id": "wonyotti",                  // 🆕
  "inferred_persona": "MODERATE",           // 🆕
  "persona_override_reason": null,          // 🆕
  "llm_proposal": {...},                    // 🆕
  "risk_assessment": {...},                 // 🆕
  "risk_tool_calls": [...],                 // 🆕
  "evaluator_review": {                     // 🆕
    "summary": "...",
    "user_message": "...",
    "reason_codes": [...],
    "schema_warnings": []
  }
}
```

### 5.4 AI → BE 도구 호출 (Phase 2 신규 방향)

```
AI risk_agent → POST {BE_URL}/tools/market/volatility { symbol, days, run_id }
              ← BE가 Binance Testnet에서 가져와 응답
```

이 방향은 **MVP에서는 사용 안 함** (mock fixture로 대체).

---

## §6. 작업 분담 (Phase 2 진입 시)

| 저장소 | 담당 | MVP 산출 | Phase 2 산출 |
|---|---|---|---|
| autocoin-ai | 본인 | 새 흐름 + 6 시나리오 + 영상 | (변경 없음) |
| autocoin-api | BE 팀원 | (변경 없음) | tool proxy 5개 + market_snapshot + persona_default + SSE |
| autocoin-web | FE 팀원 | (변경 없음) | 챗 UI + persona 프로필 + trace 시각화 |

---

## §7. 평가/제출 시 설명 멘트

평가자가 "이 변경이 BE/FE에 어떤 영향을 주나요?"라고 물으면:

> **MVP에서는 BE/FE 변경 없습니다.** AI 저장소 안에서 격리되어 동작하며, mock fixture와 CLI 데모로 시연합니다.
> 
> **Phase 2 후속**으로 BE는 5개 tool proxy endpoint와 market_snapshot 패키징, FE는 챗 UI와 trace 시각화가 추가됩니다. 사양은 `docs/DOWNSTREAM.md`에 명세되어 있습니다.
>
> 기존 BE/FE는 새 흐름과 **완전 호환**됩니다. 인풋이 dict든 text든 intake 노드가 양쪽 모두 처리합니다.

---

## §8. 정리

| 질문 | 답 |
|---|---|
| MVP가 BE 코드 건드리나요? | **아니오**. 0줄. |
| MVP가 FE 코드 건드리나요? | **아니오**. 0줄. |
| 그럼 자연어는 어떻게 받나요? | `examples/*.json`의 `request_context.user_input.text`로 직접. CLI 데모. |
| 도구는 어떻게 동작하나요? | `tools/_mock_data.py`의 fixture로 결정론 응답. |
| 데모는 어떻게 보여주나요? | CLI 실행 영상 1~3분. README의 "실행 결과" 섹션. |
| Phase 2 BE/FE 작업 시간은? | BE ~10h, FE ~30h. **다음 스프린트 분량**. |

> **MVP는 격리된 단일 저장소 제출이고, Phase 2는 통합 사양만 사전 정의된 상태**다.
