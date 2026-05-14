# autocoin-ai 문서

> Coin Agent / Binance Spot Testnet 범위 안에서 AI 계층을 중심으로 정리한 최소 canonical 문서 세트

## 문서 목적

이 문서는 `autocoin-ai` 서브프로젝트의 진입점이다. 이 서브프로젝트는 Coin Agent 전체 범위 중 AI 중심 책임을 다루며, 가상 자금 기반 현물 주문 테스트만 지원한다. 기획 배경과 범위 요약은 이 문서와 `SPEC.md`에 압축해 둔다.

## 관련 문서

- 범위와 요구사항: `SPEC.md`
- 책임 경계와 흐름: `ARCHITECTURE.md`
- FE boundary 계약: `FE.md`
- BE boundary 계약: `BE.md`
- AI 계층 기준: `AI.md`
- 데이터와 상태 계약: `DATA.md`
- 검증과 데모 기준: `TEST_AND_DEMO.md`

## 서브프로젝트 한 줄 정의

`autocoin-ai`는 Binance Spot Testnet 전용 Coin Agent에서 정책 해석, 리스크 게이트, 설명 가능한 판단 trace, run resume 흐름을 담당하는 AI 중심 서브프로젝트다.

## 범위 요약

- 거래소 범위는 Binance Spot Testnet만 사용한다.
- 주문 범위는 가상 자금 기반 현물 주문 테스트만 다룬다.
- AI는 판단 보조와 게이트 역할을 맡고, 최종 제출 권한은 BE에 있다.
- FE는 입력과 시각화만 담당하며 Binance를 직접 호출하지 않는다.
- 실거래, 선물, 마진, 출금, 레버리지는 문서 범위에서 제외한다.

## 고정 안전 규칙

| 구분 | 값 |
|---|---|
| REST Base URL | `https://testnet.binance.vision/api` |
| WebSocket Streams | `wss://stream.testnet.binance.vision/ws` |
| WebSocket API | `wss://ws-api.testnet.binance.vision/ws-api/v3` |

다음 항목은 허용하지 않는다.

- Production Binance host
- 실거래 API Key / Secret
- live trading 문맥
- futures, margin, withdraw, leverage

## canonical 용어

이 서브프로젝트 문서는 다음 용어를 그대로 유지한다.

- `run_id`
- `policy_context`
- `decision_trace`
- `verification_checks`
- `hold_reason`
- `HOLD_REVIEW_REQUIRED`
- `HOLD_DATA_INSUFFICIENT`
- `READY_FOR_BE`
- `BE_REJECTED`
- `FAILED`
- `REPORT_READY`
- `NO_ORDER`

## human QA와 rehearsal 원칙

이 서브프로젝트는 AI 중심 저장소여도 happy path만 확인하고 끝내지 않는다. 정책별 workflow 차이, `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `BE_REJECTED`, `FAILED`, same `run_id` resume 흐름은 사람이 반복 가능한 시나리오로 검증해야 하며, 세부 기준은 `TEST_AND_DEMO.md`를 따른다.

## 문서 읽는 순서

1. `README.md`
2. `SPEC.md`
3. `ARCHITECTURE.md`
4. `FE.md`
5. `BE.md`
6. `AI.md`
7. `DATA.md`
8. `TEST_AND_DEMO.md`

## 문서 권한 맵

- 범위와 완료 기준은 `SPEC.md`가 소유한다.
- 시스템 흐름과 lifecycle 큰 그림은 `ARCHITECTURE.md`가 소유한다.
- FE 입력/표시 boundary는 `FE.md`가 소유한다.
- BE 검증/실행 boundary는 `BE.md`가 소유한다.
- AI 상태 해석과 resume 규칙은 `AI.md`가 소유한다.
- canonical 필드, 상태, payload shape은 `DATA.md`가 소유한다.
- acceptance와 rehearsal 기준은 `TEST_AND_DEMO.md`가 소유한다.

## 이 문서 세트의 초점

이 문서 세트는 AI 중심 저장소에 맞춰 작성한다. 다만 end-to-end 구현과 리뷰가 가능하도록 FE와 BE는 새 기능 명세가 아니라 boundary-only 계약 문서로 포함한다. 이 문서 세트만 읽어도 FE->BE->AI 책임 경계, 상태 vocabulary, acceptance 기준을 해석할 수 있어야 한다.
