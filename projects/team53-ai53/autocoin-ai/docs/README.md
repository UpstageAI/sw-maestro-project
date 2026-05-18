# autocoin-ai 문서

> Coin Agent의 standalone AI HTTP 서비스와 agentic run orchestration 구현 기준 문서 세트

## 문서 목적

이 문서는 `autocoin-ai` 저장소의 실제 구현 상태를 기준으로 AI 서비스의 책임, HTTP 인터페이스, 상태 모델, fallback, checkpoint, 제약 사항을 설명한다.

## 현재 구현 요약

- standalone HTTP AI 서비스
- `/runs/start`, `/runs/agentic/start`, `/runs/resume`, `/runs/complete`
- `/runs/{run_id}/checkpoints/order`, `/runs/{run_id}/checkpoints/completion`
- non-agentic run resume 지원
- agentic run resume 미지원
- 로컬 JSON run store 사용
- 자연어 intake fallback, live snapshot 기반 strategy/risk grounding, evaluator fallback 구현

## 관련 문서

- `SPEC.md` — 저장소 범위와 완료 기준
- `ARCHITECTURE.md` — graph, HTTP surface, 상태 흐름
- `AI.md` — AI 책임 경계와 HTTP 계약
- `DATA.md` — state/model/trace vocabulary
- `ENV.md` — Gemini / run store 환경 변수
- `TEST_AND_DEMO.md` — 테스트/데모 기준

## 책임 경계

- AI는 Binance를 직접 호출하지 않는다.
- AI는 서명, timestamp, API Key 관리를 하지 않는다.
- AI는 `READY_FOR_BE` 또는 `HOLD` / `NO_ORDER` 같은 판단 결과를 생성한다.
- 실제 제출 여부와 Binance Testnet 호출은 BE만 수행한다.

## 현재 HTTP 인터페이스

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/runs/start` | non-agentic run 시작 |
| POST | `/runs/agentic/start` | 자연어/agentic run 시작 |
| POST | `/runs/resume` | non-agentic hold run 재개 |
| POST | `/runs/complete` | BE execution/rejection 결과 주입 |
| GET | `/runs/{run_id}/checkpoints/order` | order graph checkpoint evidence |
| GET | `/runs/{run_id}/checkpoints/completion` | completion graph checkpoint evidence |

## 현재 구현 제약

- agentic run resume 는 현재 지원되지 않는다.
- live snapshot 이 주입되지 않으면 strategy/risk 판단은 더 보수적으로 HOLD 쪽으로 기울 수 있다.
- risk tool registry 에는 여전히 mock 도구가 존재하지만, 최신 auto-trading path 에서는 BE가 주입한 live snapshot 을 strategy/risk 단계가 우선 참고한다.

## 문서 초점

이 저장소 문서는 “AI가 무엇을 할 수 있는가”보다 “AI가 어디까지 하고 어디서 멈추는가”를 정확히 적는 것을 우선한다. 특히 `READY_FOR_BE`, `HOLD`, `FAILED`, resume 제약, checkpoint evidence, BE handoff는 구현 기준 그대로 유지해야 한다.
