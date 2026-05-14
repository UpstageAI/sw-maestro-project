# Coin Agent 제품/기능 명세

## 문서 목적

이 문서는 Binance Spot Testnet 전용 Coin Agent의 제품 요구사항과 MVP 범위를 정의한다. 이 문서는 **가상 자금 기반 현물 주문 테스트**를 위한 기능만 다루며, 실거래 기능은 포함하지 않는다.

## 관련 문서

- 상위 근거: `PROPOSAL.md`
- 시스템 구조: `ARCHITECTURE.md`
- 계약 기준: `DATA.md`
- 테스트 기준: `TEST_AND_DEMO.md`

## 1. 프로젝트 목표

Coin Agent의 목표는 사용자가 Binance Spot Testnet 환경에서 잔고 조회, 시세 조회, 현물 매수/매도 주문, 주문 상태 조회, 주문 취소, WebSocket 시세 수신 흐름을 안전하게 테스트할 수 있도록 돕는 것이다.

## 2. 대상 사용자

- 로컬 환경에서 개인용 Agent를 직접 실험하려는 사용자
- 실거래 전 단계에서 Spot Testnet으로 주문 흐름을 검증하려는 사용자
- REST/WebSocket 기반 거래소 연동을 빠르게 이해하고 싶은 사용자

## 3. MVP 범위

### 3.1 반드시 포함할 범위

- Binance Spot Testnet API Key/Secret 설정
- 계정 잔고 조회
- 현재가 조회
- 호가 조회
- 캔들 조회
- 현물 매수 주문 테스트
- 현물 매도 주문 테스트
- 주문 상태 조회
- 주문 취소
- WebSocket ticker 또는 bookTicker 수신
- Python 예제 코드 제공

### 3.2 제외 범위

- 실거래 계정 연동
- Binance Production 엔드포인트 사용
- 선물, 마진, 출금, 레버리지
- 자동 실주문 전략 운용
- 다중 거래소 연동

## 4. 핵심 사용자 시나리오

### US-01 Testnet API Key 설정

사용자는 Binance Spot Testnet에서 발급받은 API Key/Secret을 로컬 환경 변수에 설정할 수 있어야 한다.

### US-02 잔고와 시세 확인

사용자는 주문 전에 Testnet 잔고, 현재가, 호가, 캔들 데이터를 확인할 수 있어야 한다.

### US-03 시장가 또는 지정가 주문 테스트

사용자는 `BTCUSDT` 같은 심볼로 현물 매수/매도 주문을 테스트하고, 결과를 확인할 수 있어야 한다.

### US-04 주문 상태 조회 및 취소

사용자는 `orderId` 또는 `origClientOrderId`를 기준으로 주문 상태를 조회하고, 필요 시 취소할 수 있어야 한다.

### US-05 WebSocket 시세 수신

사용자는 WebSocket stream을 통해 시세 이벤트를 수신하고, FE에서 이를 시각적으로 확인할 수 있어야 한다.

## 5. 사용자 정책 정의

이 프로젝트에서 사용자 정책은 투자 전략이 아니라 **주문 테스트 제한 규칙**으로 정의한다.

AI는 이 정책을 완화하거나 재정의하지 않고, 구조화된 주문 테스트 요청이 이 정책 안에 있는지만 판단한다.

- 테스트 대상 심볼 목록
- 허용 주문 유형 (`MARKET`, `LIMIT`)
- 허용 최대 수량 또는 최대 quote 금액
- 주문 테스트 허용 시간대
- 자동 주문 테스트 활성 여부
- 주문 실패 시 기본 동작 (`무주문`, `취소`, `재시도 없음`)

정책 입력은 단일 프롬프트 문자열이 아니라 검색 가능한 policy artifact 집합으로 취급한다. Policy/Planning Agent는 요청마다 관련 정책 조각을 조회해 `policy_context`를 만들고, 그 근거를 `decision_trace.policy`와 `verification_checks`에 남겨야 한다.

정책 위반 또는 근거 부족으로 즉시 진행할 수 없는 경우, 시스템은 단순 실패 대신 다음 두 가지 보류 이유를 구분해야 한다.

- `HOLD_REVIEW_REQUIRED`: 사람 승인 또는 운영자 검토가 필요한 경우
- `HOLD_DATA_INSUFFICIENT`: 시장 데이터, 응답 필수 필드, 정책 입력이 부족해 재조회/재입력이 필요한 경우

## 6. 리스크 원칙

- Testnet 전용
- 실거래 금지
- 잘못된 심볼/수량/가격 조건이면 주문 요청 차단
- 필수 파라미터 누락 시 무주문 또는 판단 보류
- API 실패 시 신규 주문 테스트 중단
- AI 판단 결과가 `PASS`여도 BE가 제출 직전에 다시 검증한다.
- AI는 시그니처 생성, 실거래 전환, 리스크 게이트 우회를 수행하지 않는다.
- LLM은 action proposal 또는 action path를 만들 수 있지만, gate 판단은 AI가 수행하고 실행 결정권은 BE의 deterministic 재검증과 제출 단계에 있다.

## 7. 기능 요구사항

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| FR-01 | 사용자는 Binance Spot Testnet API Key/Secret을 설정할 수 있어야 한다. | 환경 변수 기준으로 설정을 완료할 수 있어야 한다. |
| FR-02 | 시스템은 Testnet 계정 잔고를 조회할 수 있어야 한다. | `asset`, `free`, `locked`가 반환되어야 한다. |
| FR-03 | 시스템은 현재가를 조회할 수 있어야 한다. | `symbol` 기준 현재가가 반환되어야 한다. |
| FR-04 | 시스템은 호가를 조회할 수 있어야 한다. | bid/ask 가격과 수량을 확인할 수 있어야 한다. |
| FR-05 | 시스템은 캔들 데이터를 조회할 수 있어야 한다. | `interval` 기준 OHLCV가 반환되어야 한다. |
| FR-06 | 시스템은 Spot 시장가 매수/매도 주문을 테스트할 수 있어야 한다. | 주문 응답에서 `orderId`, `status`를 확인할 수 있어야 한다. |
| FR-07 | 시스템은 Spot 지정가 주문을 테스트할 수 있어야 한다. | `price`, `timeInForce`, `quantity` 기반 요청이 가능해야 한다. |
| FR-08 | 시스템은 주문 상태를 조회할 수 있어야 한다. | `GET /api/v3/order` 기반 상태 확인이 가능해야 한다. |
| FR-09 | 시스템은 주문을 취소할 수 있어야 한다. | 취소 응답에서 취소 결과를 확인할 수 있어야 한다. |
| FR-10 | 시스템은 WebSocket 시세 stream을 수신할 수 있어야 한다. | `ticker`, `bookTicker`, `kline` 중 하나 이상 수신해야 한다. |
| FR-11 | 시스템은 Python 예제 코드를 제공해야 한다. | 공식 문서 기반 테스트넷 예제가 포함되어야 한다. |
| FR-12 | 시스템은 실거래 URL/API Key 사용을 금지해야 한다. | 문서와 구현 기준에서 production URL/key 사용 금지 경고가 포함되어야 한다. |
| FR-13 | 시스템은 AI run을 `run_id` 기준으로 추적하고 재개할 수 있어야 한다. | 주문 테스트 요청과 실행 결과 주입이 동일 `run_id` 아래에서 이어져야 한다. |
| FR-14 | 시스템은 `HOLD`를 보류 이유별로 구분해야 한다. | `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT` 중 하나가 함께 기록되어야 한다. |
| FR-15 | 시스템은 AI 산출물을 구조화 schema로 검증해야 한다. | 노드 출력이 사전 정의된 schema 또는 모델 이름에 매핑되어야 한다. |
| FR-16 | 시스템은 AI 판단 근거와 검증 결과를 단계별 trace로 남겨야 한다. | `reason_codes`, `evidence_refs`, `verification_checks`, `final_action`가 run 로그에 포함되어야 한다. |
| FR-17 | 시스템은 BE 재검증 또는 schema 검증 실패를 구분해 기록해야 한다. | `BE_REJECTED`, `FAILED`, `HOLD_*` 상태가 혼동 없이 구분되어야 한다. |
| FR-18 | 시스템은 Policy/Planning 단계에서 정책 검색 또는 RAG grounding 흐름을 지원해야 한다. | `policy_context`의 출처와 적용 규칙이 trace로 확인 가능해야 한다. |
| FR-19 | 시스템은 evaluator/reflection 루프를 통해 trace 품질과 실행 적합성을 재평가해야 한다. | 평가 대상, 점수, retry 여부, 실패 전이가 run 기록에 남아야 한다. |
| FR-20 | 시스템은 리포트 단위와 cadence를 고정해야 한다. | 1 `run_id` 단위 최종 리포트와 단계별 중간 보고 시점이 문서화되어야 한다. |
| FR-21 | 시스템은 정책별 데모와 휴먼 QA 절차를 제공해야 한다. | 서로 다른 정책에서 서로 다른 흐름이 재현되고, 사람 검수가 체크리스트로 수행 가능해야 한다. |

## 8. 비기능 요구사항

| ID | 요구사항 | 기준 |
|---|---|---|
| NFR-01 | 안전성 | 실거래 URL과 실거래 키를 사용하지 않아야 한다. |
| NFR-02 | 일관성 | 모든 문서의 엔드포인트와 심볼 예시가 Binance Spot Testnet 기준으로 일치해야 한다. |
| NFR-03 | 추적 가능성 | 주문 요청, gate 결과, 무주문 사유, 주문 결과, 취소 결과를 로그로 남겨야 한다. |
| NFR-04 | 단순성 | 로컬 개인용 Agent에 맞게 SQLite + HTTP 구조를 유지해야 한다. |
| NFR-05 | 실행 권한 분리 | AI는 판단과 설명만 담당하고, BE만 Binance 제출과 서명을 수행해야 한다. |
| NFR-06 | 상태 일관성 | 동일 `run_id`의 checkpoint, resume, 결과 주입이 상태 전이 규칙과 충돌하지 않아야 한다. |
| NFR-07 | 출력 안정성 | 구조화 출력 schema mismatch가 발생하면 조용히 무시하지 않고 `FAILED` 또는 `HOLD` + `hold_reason=HOLD_DATA_INSUFFICIENT`로 처리해야 한다. |
| NFR-08 | 검증 가능성 | `PASS`, `NO_ORDER`, `HOLD_*`, `BE_REJECTED`, `FAILED`에 대한 테스트 시나리오가 문서화되어야 한다. |
| NFR-09 | 권한 경계 명확성 | Agent별 허용 도구와 금지 행위, BE의 실행 권한이 문서상 명확해야 한다. |
| NFR-10 | QA 재현성 | 사람 중심 QA가 같은 정책과 같은 기대 상태로 반복 가능해야 한다. |

## 9. 핵심 기능 목록

1. API Key 설정
2. 계정 잔고 조회
3. 현재가/호가/캔들 조회
4. Spot 매수/매도 주문 테스트
5. 주문 상태 조회
6. 주문 취소
7. WebSocket 시세 수신
8. Python 예제 실행

## 10. MVP 완료 기준

1. Spot Testnet Key 설정 가능
2. 잔고 조회 성공
3. 가격/호가/캔들 조회 성공
4. Spot 매수/매도 주문 테스트 성공
5. 주문 상태 조회 성공
6. 주문 취소 성공
7. WebSocket 시세 수신 성공
8. 어떤 문서에도 실거래 엔드포인트가 남아 있지 않음
9. AI run의 `run_id`, `gate_decision`, `hold_reason`, `decision_trace`가 추적 가능함
10. BE 재검증 실패와 데이터 부족 보류가 서로 다른 최종 상태로 설명됨

## 11. 성공 지표

- 핵심 시나리오 5개 end-to-end 동작
- 실거래 URL/API Key 사용 0건
- 테스트넷 엔드포인트 표기 오류 0건
- 주문/상태/취소 예시 문서화 완료
- `PASS`, `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `BE_REJECTED` 케이스별 기대 결과 문서화 완료

## 12. 확정 구현 기준

- 거래소는 Binance Spot Testnet만 사용한다.
- 기본 테스트 심볼 예시는 `BTCUSDT`, `ETHUSDT`를 사용한다.
- 주문 테스트는 시장가와 지정가 현물 주문까지만 다룬다.
- 심볼은 REST에서 대문자, WebSocket stream에서 소문자를 사용한다.
- 리포트와 로그는 주문 테스트 결과 설명에 집중한다.
- AI의 허용 판단은 advisory이며, BE 재검증을 통과해야만 주문 테스트가 실제 제출된다.
- `HOLD`는 최소한 `HOLD_REVIEW_REQUIRED`와 `HOLD_DATA_INSUFFICIENT`로 세분화해 해석 가능해야 한다.
- AI 노드 출력은 이름 있는 schema 계약을 따라야 하며, FE/BE/AI가 같은 용어를 사용해야 한다.
- canonical 리포트 cadence는 request accepted, policy retrieval complete, policy complete, risk gate complete, evaluator complete, BE revalidation complete, final report ready 순서를 기준으로 정의한다.
- FE 요약이나 간단 리포트는 위 cadence의 subset만 보여줄 수 있지만, 저장과 검증 기준은 canonical cadence를 따른다.