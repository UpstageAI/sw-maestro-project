# Coin Agent AI 서비스 명세

## 문서 목적

이 문서는 현재 구현 기준의 AI 계층 책임과 HTTP 계약을 설명한다. 핵심은 AI가 Binance 제출 권한이 없는 판단/trace 서비스라는 사실, 그리고 자연어 입력에서 trader/persona 를 추론해 같은 세션의 판단 스타일 힌트를 만드는 역할까지 맡는다는 점을 분명히 유지하는 것이다.

## 1. AI의 역할

- 자연어 또는 구조화 입력을 주문 의도로 정규화
- 정책과 trader 원칙 기반 strategy/risk 판단
- 자연어 문장에서 trader style 을 읽고 `traderId`, `inferredPersona` 를 추론
- hold/no-order/ready-for-be 분기 생성
- BE completion payload 기반 결과 해석과 report 보강

## 2. 권한 경계

- AI는 Binance를 직접 호출하지 않는다.
- AI는 서명을 생성하지 않는다.
- AI는 최종 실행 승인자가 아니다.
- 실제 제출은 BE만 수행한다.

## 3. 현재 구현 형태

- standalone HTTP 서비스
- non-agentic graph 와 agentic graph 둘 다 제공
- 로컬 JSON run store 사용
- HTTP startup 시 `.env` 로드

## 4. HTTP 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/runs/start` | non-agentic run 시작 |
| POST | `/runs/agentic/start` | 자연어/agentic run 시작 |
| POST | `/runs/resume` | non-agentic hold run 재개 |
| POST | `/runs/complete` | BE execution/rejection 결과 반영 |
| GET | `/runs/{run_id}/checkpoints/order` | order graph checkpoint evidence |
| GET | `/runs/{run_id}/checkpoints/completion` | completion graph checkpoint evidence |

## 5. agentic graph 요약

- `intake`
- `policy`
- `strategy`
- `risk_agent`
- `risk_gate`
- `evaluator`

현재 주요 구현 사실:

- intake 는 natural language parse, heuristic fallback, ambiguity HOLD 처리
- intake / strategy 단계에서는 사용자의 문장에서 trader/persona 단서를 읽어 이후 판단 스타일에 반영할 수 있다.
- strategy 는 live snapshot 을 prompt에 포함해 판단
- strategy LLM 실패 시 deterministic fallback 가능
- risk_gate 는 live account/market snapshot 이 있으면 그것을 우선 사용하고, 없으면 mock tool fallback 사용

## 6. 상태와 제약

주요 상태:

- `HOLD`
- `READY_FOR_BE`
- `NO_ORDER`
- `BE_REJECTED`
- `FAILED`
- `REPORT_READY`

주요 hold reason 예시:

- `HOLD_INPUT_AMBIGUOUS`
- `HOLD_LOW_CONVICTION`
- `HOLD_RISK_AGENT_FLAGGED`
- `HOLD_DATA_INSUFFICIENT`

이 상태 구조는 evidence 가 약하거나 충돌할 때 억지 제출보다 `HOLD` 또는 `NO_ORDER` 를 선호하는 현재 구현 원칙과 맞물린다.

중요 제약:

- agentic run resume 는 현재 지원되지 않는다.
- `complete()` 는 `READY_FOR_BE` 에서만 허용된다.
- checkpoint completion evidence 는 completion 이후에만 조회 가능하다.

## 7. BE handoff 의미

- AI가 `READY_FOR_BE` 를 반환해도 그것은 제출 완료가 아니다.
- BE는 그 뒤 `normalized_order_intent` 를 실제 주문 요청으로 변환하고, defensive rule base 와 deterministic 재검증 후에만 Binance Testnet에 제출한다.
- `execution.py` 는 completion payload 를 해석할 뿐, 직접 제출하지 않는다.

## 8. 현재 문서화 시 주의할 오해

- AI가 주문을 직접 넣는다고 쓰면 안 된다.
- AI가 live market/account 데이터의 유일한 source 라고 쓰면 안 된다. 최신 auto-trading path 에서는 BE가 live snapshot 을 수집해 AI에 주입한다.
- agentic resume 가 되는 것처럼 쓰면 안 된다.
- persona 전용 화면 선택기가 이미 있는 것처럼 쓰면 안 된다. 현재 persona 는 자연어 입력과 AI 추론 결과로 드러나는 개념이다.
- 시간 누적 report history 를 AI가 이미 계산하는 것처럼 쓰면 안 된다. 현재는 run 단위 report 보강이 기준이다.
