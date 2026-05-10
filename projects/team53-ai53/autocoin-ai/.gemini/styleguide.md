# Gemini Code Review Style Guide

이 문서는 `autocoin-ai` 저장소의 Gemini code review 기준을 정의한다.

---

## Review Comment Style & Language

- 모든 리뷰 코멘트는 **한국어로 작성한다.**
- 코멘트에는 **무엇이 어긋났는지**, **왜 문제인지**, **어떻게 맞추면 되는지**를 함께 적는다.
- 사소한 제안에는 `[nit]` 접두어를 붙인다.
- 다른 Git repo 문서를 이 저장소의 내장 기준처럼 단정하지 않고, **로컬 참고 문서 기준으로 볼 때**라는 식으로 표현한다.
- 이 저장소 리뷰에서는 **범위 통제**, **아키텍처 책임 경계**, **데이터 계약 정합성**, **테스트 시나리오 보존**을 우선 검증한다.

---

## 1) 제품/범위 규칙

다음 항목은 모든 코드 리뷰에서 기본 전제로 유지되어야 한다.

- 프로젝트 범위는 **Coin Agent / Binance Spot Testnet 전용**이다.
- 실거래 URL, 실거래 API Key / Secret, 선물, 마진, 출금, 레버리지 기능은 허용하지 않는다.
- 모든 주문/체결 흐름은 **가상 자금 기반 현물 주문 테스트**만 다룬다.

### 리뷰 체크포인트

| 검사 항목 | 규칙 |
|---|---|
| 거래 범위 | 실거래 기능이나 Production Binance Host 가 diff 에 섞이면 안 된다. |
| 기능 범위 | futures, margin, withdraw, leverage 관련 구현이나 문구가 추가되면 안 된다. |
| 테스트/데모 범위 | 테스트와 데모는 Spot Testnet 전용 흐름만 유지해야 한다. |

---

## 2) 아키텍처 책임 경계

- **FE는 Binance API를 직접 호출하면 안 된다.**
- **BE만** Binance 연동, 서명, 주문 제출, 재검증을 수행할 수 있다.
- **AI는 판단 보조 및 게이트 역할만 수행**하며, 직접 주문을 실행하거나 BE 검증을 우회할 수 없다.

### 리뷰 체크포인트

| 검사 항목 | 규칙 |
|---|---|
| FE 책임 | FE 코드에 Binance 직접 호출, API Key 처리, 서명 로직이 들어가면 안 된다. |
| BE 책임 | 주문 제출과 최종 실행 판단은 항상 BE에 남아 있어야 한다. |
| AI 책임 | AI가 주문 실행 주체처럼 서술되거나 구현되면 안 된다. |

---

## 3) 데이터/API 정합성

다음 값과 용어는 로컬 참고 문서 기준과 일치해야 한다.

| 항목 | 규칙 |
|---|---|
| REST Base URL | `https://testnet.binance.vision/api` |
| WebSocket Streams | `wss://stream.testnet.binance.vision/ws` |
| WebSocket API | `wss://ws-api.testnet.binance.vision/ws-api/v3` |
| REST 심볼 예시 | `BTCUSDT`, `ETHUSDT`처럼 대문자 |
| Stream 이름 예시 | `btcusdt@ticker`처럼 소문자 |

### 용어 체크포인트

- `run_id`, `policy_context`, `decision_trace`, `hold_reason` 같은 필드명은 임의로 바꾸면 안 된다.
- `BE_REJECTED`, `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `REPORT_READY`, `NO_ORDER` 같은 핵심 상태명은 로컬 참고 문서 기준과 맞아야 한다.
- `PASS`는 최종 체결 승인과 동의어가 아니며, 최종 실행 권한은 항상 BE에 있다.
- `orderbook` 관련 용어는 `depth` 기준과 충돌하지 않아야 한다.

---

## 4) 테스트 및 데모 보존 규칙

- 테스트 예시, 데모 스크립트, 샘플 환경 변수는 Testnet 기준만 사용해야 한다.
- 정상 흐름뿐 아니라 `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `BE_REJECTED`, resume with same `run_id` 같은 비정상/보류 흐름도 보존되어야 한다.
- 요청 수락부터 최종 보고까지의 canonical 리포트 흐름을 깨는 변경은 지적해야 한다.

---

## 5) 리뷰에서 특히 중요한 실패 유형

다음 항목은 우선적으로 지적한다.

1. **실거래 범위 혼입**
   - Production URL, 실거래 키, 실거래 주문 맥락이 들어오는 경우
2. **책임 경계 붕괴**
   - FE가 Binance를 직접 호출하거나, AI가 실행 주체가 되는 경우
3. **계약/용어 불일치**
   - 상태명, 필드명, 심볼 casing, 엔드포인트가 로컬 참고 문서 기준과 달라지는 경우
4. **테스트 시나리오 후퇴**
   - 보류/거절/resume 흐름이 빠지거나 Spot Testnet 전용 규칙이 깨지는 경우

---

## 6) 리뷰 코멘트 예시

- `이 변경은 FE 레이어에서 Binance 엔드포인트를 직접 호출하고 있어 ARCHITECTURE.md의 책임 경계와 충돌합니다. Binance 연동과 서명은 BE 전용이므로, FE에서는 BE API를 호출하는 구조로 되돌리는 편이 맞습니다.`
- `이 테스트는 Production Binance URL을 예시로 사용하고 있어 README와 TEST_AND_DEMO.md의 Spot Testnet only 규칙을 깨고 있습니다. testnet 호스트로 교체하지 않으면 범위가 달라집니다.`
- `[nit] 로컬 참고 DATA 문서 기준으로 보면 상태값 이름이 다릅니다. 같은 개념이면 hold_reason / BE_REJECTED처럼 기존 용어를 그대로 유지하는 편이 문서와 구현의 정합성에 유리합니다.`

---

## 확정 구현 기준

리뷰는 다음 조건을 모두 만족할 때 통과로 본다.

- Coin Agent / Binance Spot Testnet 문맥이 유지된다.
- FE / BE / AI 책임 경계가 유지된다.
- 엔드포인트, 심볼 casing, 상태명, 필드명이 로컬 참고 문서 기준과 일치한다.
- 테스트와 데모가 Testnet 전용 및 비정상 흐름 기준을 유지한다.
