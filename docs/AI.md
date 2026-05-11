# autocoin-ai 구현 명세

## 문서 목적

이 문서는 `autocoin-ai` 저장소의 실제 구현 기준 AI 서비스 동작을 설명한다. 여기서 중요한 것은 AI가 자연어 해석과 판단은 수행하지만 Binance 제출 권한은 없다는 점이다.

## 현재 구현 핵심

- standalone HTTP 서비스
- `/runs/start`, `/runs/agentic/start`, `/runs/resume`, `/runs/complete`
- `/runs/{run_id}/checkpoints/order`, `/runs/{run_id}/checkpoints/completion`
- non-agentic resume 지원
- agentic resume 미지원
- `.env` 로드 및 로컬 JSON run store 사용

## agentic 흐름

1. intake
2. policy
3. strategy
4. risk_agent
5. risk_gate
6. evaluator

### 현재 중요한 구현 사실

- intake 는 LLM 기반 parse 이전/이후에 heuristic fallback 을 가진다.
- ambiguity 가 높아도 symbol/side/amount 가 명확하면 휴리스틱으로 계속 진행할 수 있다.
- strategy 는 live market/account snapshot 을 prompt 에 포함한다.
- strategy LLM 실패 시 deterministic fallback 을 사용한다.
- risk_gate 는 live snapshot 이 있으면 우선 사용하고, 없으면 mock tool fallback 을 사용한다.
- completion 은 BE가 주입한 실행 결과 또는 차단 근거만 해석한다.

## 권한 경계

- AI는 Binance를 직접 호출하지 않는다.
- AI는 서명하지 않는다.
- AI는 `READY_FOR_BE`, `HOLD`, `NO_ORDER`, `FAILED` 같은 판단 결과를 생성한다.
- BE만 실제 제출 여부를 결정한다.

## 현재 제약

- agentic run resume 는 현재 미지원
- live snapshot 이 주입되지 않으면 보수적 `HOLD` 가능성이 커진다.
- published report 에는 intake/strategy trace 가 직접 노출되지 않는다.
