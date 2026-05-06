# Coin Agent 문서 레포지토리

> Binance Spot Testnet 전용 가상 자금 현물 주문·체결 테스트 기반 개인용 투자 보조 Agent 구현 문서 모음

## 문서 목적

이 문서는 Coin Agent 문서 레포지토리의 진입점이다. 읽는 순서, 공통 안전 수칙, 문서별 역할을 빠르게 파악할 수 있도록 안내하며, 상세 구현 기준은 각 canonical 문서를 참조한다.

## 관련 문서

- 기획 배경: `PROPOSAL.md`
- 제품/기능 요구사항: `SPEC.md`
- 시스템 구조와 책임 경계: `ARCHITECTURE.md`
- 역할별 구현 기준: `FE.md`, `BE.md`, `AI.md`
- API / 데이터 계약: `DATA.md`
- 테스트 / 데모 기준: `TEST_AND_DEMO.md`

## 절대 금지 사항

- 실거래 URL 사용 금지
- 실거래 API Key / Secret 사용 금지
- Binance Production REST/WebSocket Host 사용 금지
- 선물, 마진, 출금, 레버리지 관련 기능 문서화 금지

## 모의투자 전용 엔드포인트

| 구분 | 엔드포인트 |
|---|---|
| REST Base URL | `https://testnet.binance.vision/api` |
| WebSocket Streams | `wss://stream.testnet.binance.vision/ws` |
| WebSocket API | `wss://ws-api.testnet.binance.vision/ws-api/v3` |

## 문서 읽는 순서

1. `PROPOSAL.md` - 프로젝트 목적과 Testnet 전용 기획 배경을 이해한다.
2. `SPEC.md` - MVP 범위와 요구사항을 확인한다.
3. `ARCHITECTURE.md` - FE, BE, AI, DB, Binance Spot Testnet의 책임 경계를 확인한다.
4. `DATA.md` - API 계약, 데이터 모델, 상태/용어 정의를 확인한다.
5. `FE.md`, `BE.md`, `AI.md` - 역할별 구현 기준을 확인한다.
6. `TEST_AND_DEMO.md` - 테스트 체크리스트와 데모 흐름을 확인한다.

## 문서 역할 요약

| 문서 | 역할 | 주요 독자 |
|---|---|---|
| `README.md` | 문서 진입점, 읽는 순서, 공통 안전 수칙 | 전원 |
| `PROPOSAL.md` | 기획 배경, 문제 정의, 프로젝트 목적 | 전원 |
| `SPEC.md` | MVP 범위, 기능/비기능 요구사항 | PM, FE, BE, AI |
| `ARCHITECTURE.md` | 전체 구조, 책임 경계, 데이터 흐름 | FE, BE, AI |
| `FE.md` | 화면, 상태, 사용자 흐름, UI 기준 | FE |
| `BE.md` | API, 검증, Testnet 연동 규칙 | BE |
| `AI.md` | Agent 구조, 리스크 게이트, 판단 결과 구조 | AI |
| `DATA.md` | API 계약, 요청/응답, 데이터 모델 | FE, BE, AI |
| `TEST_AND_DEMO.md` | 테스트 체크리스트, 데모 흐름 | 전원 |

## 공통 구현 원칙 요약

- 거래소는 Binance Spot Testnet만 사용한다.
- 모든 주문은 가상 자금 기반 현물 주문 테스트만 다룬다.
- 브라우저는 Binance API를 직접 호출하지 않고, 모든 호출은 BE를 통해 수행한다.
- AI는 판단 보조와 게이트 역할을 수행하며, 실제 실행 권한은 BE에만 있다.
- 정책 또는 리스크 게이트를 통과하지 못하면 기본값은 `NO_ORDER` 또는 `HOLD`다.

## 빠른 확인 체크리스트

- REST 심볼 예시는 `BTCUSDT`, `ETHUSDT`처럼 대문자를 사용한다.
- WebSocket stream 이름 예시는 `btcusdt@ticker`처럼 소문자를 사용한다.
- `run_id`, `hold_reason`, `decision_trace`, `BE_REJECTED` 같은 핵심 용어는 문서 간 동일하게 유지한다.
- 상세 상태 전이, checkpoint / resume, cadence 기준은 `ARCHITECTURE.md`, `AI.md`, `DATA.md`, `TEST_AND_DEMO.md`를 기준으로 본다.

## 실수 방지 주의사항

- REST 호출은 반드시 `https://testnet.binance.vision/api` 만 사용한다.
- 시세 스트림은 반드시 `wss://stream.testnet.binance.vision/ws` 만 사용한다.
- WebSocket API는 반드시 `wss://ws-api.testnet.binance.vision/ws-api/v3` 만 사용한다.
- 환경 변수 이름에 `TESTNET`이 들어간 값만 사용한다.
- 다음 값은 문서와 구현 모두에서 금지한다: `https://api.binance.com`, `wss://stream.binance.com`, `wss://ws-api.binance.com`, 실거래 Binance API Key / Secret

## 확정 구현 기준

- Coin Agent / Binance Spot Testnet 문맥을 유지한다.
- 실거래 기능, 출금, 선물, 마진, 레버리지는 문서 범위에 포함하지 않는다.
- README는 진입점과 공통 안전 수칙만 담당하고, 상세 구현 기준은 역할별 문서를 참조한다.
- 예시 URL, 심볼, 상태 용어, 책임 경계는 다른 root 문서와 서로 맞아야 한다.
