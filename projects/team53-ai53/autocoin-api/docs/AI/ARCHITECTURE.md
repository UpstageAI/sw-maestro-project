# autocoin-ai 시스템 아키텍처

## 문서 목적

이 문서는 `autocoin-ai` 서브프로젝트가 Coin Agent 전체 구조 안에서 어디에 위치하는지 설명한다. 초점은 AI 계층이며, FE와 BE는 책임 경계를 설명하는 수준으로만 다룬다.

## 관련 문서

- 문서 진입점: `README.md`
- 범위와 요구사항: `SPEC.md`
- 이 문서: `ARCHITECTURE.md`
- FE boundary 계약: `FE.md`
- BE boundary 계약: `BE.md`
- AI 계층 상세: `AI.md`
- 데이터 계약: `DATA.md`
- 테스트와 데모 기준: `TEST_AND_DEMO.md`

## 1. 구조 요약

Coin Agent의 최소 구조는 FE, BE, AI, 저장소, Binance Spot Testnet으로 나뉜다. `autocoin-ai`는 그중 AI 계층과 AI run 상태 계약을 문서화하는 서브프로젝트다.

## 2. 책임 경계

| 주체 | 핵심 책임 | 경계 |
|---|---|---|
| FE | 입력 수집, 결과 시각화 | FE는 Binance를 직접 호출하지 않는다. |
| BE | 정책 retrieval, Binance Testnet 연동, deterministic 재검증, 최종 제출 | BE만 Binance 서명과 제출 권한을 가진다. |
| AI | 정책 해석, risk gate, evaluator, report explanation | AI는 최종 실행 주체가 아니다. |

## 3. canonical 흐름

1. FE가 주문 테스트 요청을 BE에 전달한다.
2. BE가 정책 artifact를 조회해 `policy_context`를 구성한다.
3. BE가 같은 `run_id`로 AI run을 시작한다.
4. AI는 policy, risk, evaluation 단계를 거쳐 proposal 또는 보류 결과를 만든다.
5. Risk/Evaluator 단계가 proposal을 유지하면 lifecycle은 `READY_FOR_BE`로 정리된다.
6. `PASS`는 trace 또는 gate 의미이고, `READY_FOR_BE`는 lifecycle handoff 상태다.
7. BE는 `READY_FOR_BE` 이후 deterministic 재검증을 다시 수행한다.
8. BE가 승인하면 Binance Spot Testnet 제출로 이어진다.
9. BE가 차단하면 상태는 `BE_REJECTED`로 남는다.
10. AI는 resume, `execution_result`, 또는 `be_rejection_evidence`를 받아 최종 설명을 정리하고 reporting 상태를 완성한다.

## 4. 상태 경계 요약

AI 문맥에서 중요하게 유지할 상태는 다음과 같다.

- `HOLD`
- `READY_FOR_BE`
- `NO_ORDER`
- `BE_REJECTED`
- `FAILED`
- `REPORT_READY`

`HOLD`의 원인은 별도 필드 `hold_reason`으로 관리하며, 최소 집합은 `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`다. `READY_FOR_BE`는 AI 통과 후 BE 재검증 전 handoff 상태이고, `FAILED`는 schema mismatch 또는 복구 불가 기술 실패 축이다. 세부 상태 해석은 `AI.md`, 데이터 표기는 `DATA.md`를 따른다.

## 5. report cadence 요약

기본 보고 단위는 1 `run_id`다. canonical cadence는 다음 순서를 유지한다.

1. request accepted
2. policy retrieval complete
3. policy complete
4. risk gate complete
5. evaluator complete
6. BE revalidation complete
7. final report ready

중간에 `HOLD`가 발생하면 같은 `run_id`의 resume 전까지 다음 단계로 진행하지 않는다. `FAILED`가 발생하면 cadence는 terminal failure로 종료하며, `REPORT_READY`로 강제 승격하지 않는다. `NO_ORDER`와 `BE_REJECTED`는 lifecycle 종료 의미를 유지하면서도 사용자 설명 payload는 별도로 완성될 수 있다.

## 6. 고정 안전 규칙

- REST Base URL은 `https://testnet.binance.vision/api`만 사용한다.
- WebSocket Streams는 `wss://stream.testnet.binance.vision/ws`만 사용한다.
- WebSocket API는 `wss://ws-api.testnet.binance.vision/ws-api/v3`만 사용한다.
- 실거래, 선물, 마진, 출금, 레버리지는 다루지 않는다.

## 7. 이 서브프로젝트의 문서 초점

이 문서는 전체 시스템을 다시 세분화하지 않는다. FE와 BE 구현 세부는 boundary context로만 유지하고, AI run의 상태 전이와 책임 경계는 `AI.md`, canonical 필드와 상태명은 `DATA.md`, 검증 기준은 `TEST_AND_DEMO.md`를 기준으로 본다.
