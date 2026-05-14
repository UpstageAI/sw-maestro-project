# Coin Agent 테스트 및 데모 시나리오

## 문서 목적

이 문서는 Binance Spot Testnet 전용 Coin Agent의 테스트 전략, Python 예제 검증, 주문 테스트 체크리스트, 발표 데모 흐름을 정의한다.

## 관련 문서

- 요구사항: `SPEC.md`
- 데이터 계약: `DATA.md`
- 구현 기준: `FE.md`, `BE.md`, `AI.md`

## 1. 테스트 원칙

- 모든 테스트는 Binance Spot Testnet에서만 수행한다.
- 실거래 URL과 실거래 API Key는 테스트 환경에 포함하지 않는다.
- 주문 생성, 상태 조회, 주문 취소는 반드시 가상 자금 환경에서만 검증한다.
- 실거래 기능은 테스트 대상이 아니다.
- LLM 제안과 최종 실행 권한을 같은 것으로 취급하지 않는다.
- 휴먼 QA는 happy path 1회가 아니라 정책별 분기와 실패 전이를 함께 검증한다.

## 2. 핵심 기능 테스트

| 테스트 ID | 대상 | 검증 내용 | 관련 요구사항 |
|---|---|---|---|
| T-01 | API Key 설정 | Testnet Key 환경 변수 인식 | FR-01 |
| T-02 | 잔고 조회 | `GET /api/v3/account` 응답 확인 | FR-02 |
| T-03 | 현재가 조회 | `ticker/price` 응답 확인 | FR-03 |
| T-04 | 호가 조회 | `bookTicker` / `depth` 응답 확인 | FR-04 |
| T-05 | 캔들 조회 | `klines` 응답 확인 | FR-05 |
| T-06 | 현물 주문 테스트 | Spot 매수/매도 주문 성공 | FR-06, FR-07 |
| T-07 | 주문 상태 조회 | `orderId` 기준 상태 응답 확인 | FR-08 |
| T-08 | 주문 취소 | 취소 응답 확인 | FR-09 |
| T-09 | WebSocket 시세 수신 | ticker 또는 kline 이벤트 수신 | FR-10 |
| T-10 | Python 예제 | 예제 코드가 Testnet URL만 사용하는지 확인 | FR-11, FR-12 |
| T-11 | run resume | 동일 `run_id` 기준 재개 흐름 확인 | FR-13 |
| T-12 | HOLD subtype | `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT` 구분 확인 | FR-14 |
| T-13 | structured output | AI 노드 출력 schema 검증 | FR-15, FR-16 |
| T-14 | BE 재검증 분리 | `BE_REJECTED`와 일반 실패 구분 확인 | FR-17 |
| T-15 | policy retrieval grounding | Policy/Planning 단계가 관련 정책 근거를 trace에 남기는지 확인 | FR-18 |
| T-16 | evaluator loop | 평가 점수, retry, 실패 전이가 기대대로 기록되는지 확인 | FR-19 |
| T-17 | report cadence | `run_id` 단위 보고와 단계별 이벤트가 남는지 확인 | FR-20 |
| T-18 | human QA rehearsal | 다인 QA로 정책별 흐름을 재현 가능한지 확인 | FR-21 |

## 3. 테스트 체크리스트

### 환경 체크

- `BINANCE_TESTNET_REST_BASE_URL`이 `https://testnet.binance.vision/api`인지 확인
- `BINANCE_TESTNET_WS_STREAM_URL`이 `wss://stream.testnet.binance.vision/ws`인지 확인
- `BINANCE_TESTNET_WS_API_URL`이 `wss://ws-api.testnet.binance.vision/ws-api/v3`인지 확인
- API Key가 Testnet 발급 키인지 확인

### 기능 체크

- 잔고 조회 성공
- 현재가 조회 성공
- 호가 조회 성공
- 캔들 조회 성공
- 시장가 매수 주문 성공
- 시장가 매도 주문 성공
- 지정가 주문 생성 성공
- 주문 상태 조회 성공
- 주문 취소 성공
- WebSocket 이벤트 수신 성공
- 동일 `run_id` resume 성공
- HOLD 사유가 UI/API에서 구분 표시됨

### 안전 체크

- 실거래 URL 문자열 미포함
- 실거래 API Key 사용 흔적 없음
- WebSocket stream 심볼 소문자 사용 확인
- REST 심볼 대문자 사용 확인
- schema mismatch가 조용히 통과되지 않음

## 4. Agent 계약 검증 매트릭스

| 시나리오 | 입력 조건 | 기대 gate | 기대 최종 상태 | 검증 포인트 |
|---|---|---|---|---|
| A-01 | 필수 파라미터 누락 | `REJECT` 또는 `HOLD` | `NO_ORDER` 또는 `HOLD` + `hold_reason=HOLD_DATA_INSUFFICIENT` | `verification_checks.input_validation` 존재 |
| A-02 | 잔고 부족 | `REJECT` | `NO_ORDER` | `INSUFFICIENT_BALANCE` reason code 존재 |
| A-03 | stale market snapshot | `HOLD` | `HOLD` + `hold_reason=HOLD_DATA_INSUFFICIENT` | resume 필요 여부 표시 |
| A-04 | 사람 승인 필요 정책 | `HOLD` | `HOLD` + `hold_reason=HOLD_REVIEW_REQUIRED` | 승인 전 주문 미제출 |
| A-05 | AI PASS 후 BE 규칙 위반 | `PASS` | 최종 결과 `BE_REJECTED` | AI와 BE 책임 경계 구분 |
| A-06 | execution_result schema mismatch | `PASS` | `FAILED` | schema 검증 실패 로그 존재 |
| A-07 | resume 후 시장 데이터 보완 | `HOLD` | `REPORT_READY`, `BE_REJECTED`, `NO_ORDER`, `FAILED` 중 하나 | 동일 `run_id` 유지 |
| A-08 | 정책 retrieval 결과 충돌 | `HOLD` 또는 `REJECT` | `HOLD` + `hold_reason=HOLD_DATA_INSUFFICIENT` 또는 `NO_ORDER` | policy refs와 평가 로그 존재 |
| A-09 | evaluator score 미달 | `HOLD` 또는 `REJECT` | `HOLD`, `NO_ORDER` | retry 1회 이내와 실패 전이 기록 |

## 5. Python 예제 테스트

- 잔고 조회 예제 실행
- 현재가 조회 예제 실행
- 시장가 매수 예제 실행
- 주문 상태 조회 예제 실행
- 주문 취소 예제 실행
- WebSocket ticker 수신 예제 실행

## 6. Binance Spot Testnet 실패 테스트

- 잘못된 API Key 사용 시 인증 실패 확인
- 잘못된 `timestamp` 사용 시 요청 실패 확인
- 서명 누락 시 실패 확인
- 잘못된 `symbol` 사용 시 실패 확인
- 부족한 잔고에서 주문 시 실패 확인
- WebSocket 연결 실패 시 수동 조회 fallback 안내 확인
- schema 필수 필드 누락 시 `FAILED` 또는 `HOLD` + `hold_reason=HOLD_DATA_INSUFFICIENT` 확인

## 7. E2E 테스트

### E2E-01 Testnet 설정부터 잔고 조회까지

1. Testnet API Key 설정
2. `/account` 조회
3. 잔고 카드 표시 확인

### E2E-02 시세 조회부터 시장가 매수까지

1. `BTCUSDT` 현재가 조회
2. 호가 조회
3. 시장가 매수 주문 전송
4. 주문 결과 표시 확인

### E2E-03 주문 상태 조회와 취소

1. 지정가 주문 생성
2. `orderId` 기준 주문 상태 조회
3. 취소 요청
4. `CANCELED` 상태 확인

### E2E-03A 대체 식별자 기준 조회

1. 주문 생성
2. `origClientOrderId` 기준 주문 상태 조회
3. 동일 식별자로 취소 요청 가능 여부 확인

### E2E-04 WebSocket 시세 수신

1. `btcusdt@ticker` stream 연결
2. 이벤트 수신
3. FE에 최신 이벤트 표시 확인

### E2E-05 HOLD_REVIEW_REQUIRED 후 resume

1. 사람 승인 필요한 정책 조건으로 주문 요청
2. `HOLD` + `hold_reason=HOLD_REVIEW_REQUIRED` 응답 확인
3. 승인 후 같은 `run_id`로 resume
4. 이후 최종 결과 `BE_REJECTED`가 보고되거나 내부 lifecycle이 `REPORT_READY`로 마무리되는지 확인

### E2E-06 HOLD_DATA_INSUFFICIENT 후 resume

1. 데이터 부족 상태를 유도
2. `HOLD` + `hold_reason=HOLD_DATA_INSUFFICIENT` 응답 확인
3. 재조회/보완 입력 후 같은 `run_id`로 resume
4. 최종 결과가 `BE_REJECTED`, `NO_ORDER`, `FAILED` 중 하나이거나 내부 lifecycle이 `REPORT_READY`로 마무리되는 흐름이 설명 가능해야 함

### E2E-07 정책 preset 별 분기 데모

1. 자동 진행 허용 policy preset으로 주문 요청
2. AI가 action proposal을 만들고 BE 재검증 후 제출되는지 확인
3. 승인 필요 policy preset으로 같은 종류의 요청 실행
4. `HOLD` + `hold_reason=HOLD_REVIEW_REQUIRED`로 바뀌는지 확인
5. 데이터 부족 policy preset 또는 stale snapshot으로 다시 실행
6. `HOLD` + `hold_reason=HOLD_DATA_INSUFFICIENT`로 바뀌는지 확인

## 8. 발표 데모 시나리오

### 데모 1. Spot Testnet 환경 확인

- Testnet 전용 URL과 API Key 경고 배너 설명
- 환경 설정 화면 확인

### 데모 2. 잔고와 시세 조회

- `BTCUSDT` 현재가, orderbook depth, 캔들 조회
- Testnet 잔고 확인

### 데모 3. 현물 매수 주문 테스트

- 시장가 매수 주문 수행
- 주문 응답 확인
- 주문 상태 조회

### 데모 4. 주문 취소

- 지정가 주문 생성
- 취소 요청
- 취소 결과 확인

### 데모 5. WebSocket 시세 수신

- `btcusdt@ticker` 이벤트 실시간 수신 시연

### 데모 6. HOLD와 resume 시연

- 정책상 검토 필요 주문으로 `HOLD` + `hold_reason=HOLD_REVIEW_REQUIRED` 발생
- 승인 후 동일 `run_id`로 재개되는 흐름 설명

### 데모 7. 정책별 workflow 비교

- policy A: 자동 진행 허용, AI가 후보 path 제안, BE 재검증 후 제출
- policy B: 사람 승인 필요, 같은 요청이어도 `HOLD_REVIEW_REQUIRED`
- policy C: 데이터 근거 부족, `HOLD_DATA_INSUFFICIENT`
- 각 데모에서 `PASS`가 곧 주문 체결이 아님을 설명

## 9. 데모용 초기 데이터

- 기본 심볼: `BTCUSDT`, `ETHUSDT`
- 기본 interval: `1m`
- 테스트용 quote 금액: `50`
- 테스트용 수량 예시: `0.001`

## 10. 백업 플랜

- REST 호출 실패 시 직전 정상 응답 JSON을 데모용 백업으로 사용
- WebSocket 실패 시 동일 심볼의 REST 조회로 대체
- 주문 취소 실패 시 상태 조회 결과로 미체결 상태를 설명

## 11. 휴먼 QA 기대치

- 최소 2인 이상이 함께 문서, 화면, 로그를 교차 확인한다.
- 한 명은 정책/상태 전이 관점, 다른 한 명은 UI/리포트 관점으로 본다.
- QA는 `run_id`, `hold_reason`, `decision_trace`, `verification_checks`, `BE_REJECTED` 의미가 서로 어긋나지 않는지 확인해야 한다.
- 발표 직전 리허설에서도 정책별 workflow 차이를 다시 확인한다.

## 12. 확정 구현 기준

- 발표 데모는 반드시 Spot Testnet 환경에서만 수행한다.
- 예제 코드는 모두 Testnet URL만 사용한다.
- 실거래 기능은 문서와 시연 모두에서 배제한다.
- `PASS`, `NO_ORDER`, `HOLD` + `hold_reason`, `BE_REJECTED`, `FAILED`를 구분 검증한다.
- 정책 preset 이 달라지면 workflow 와 최종 상태가 달라질 수 있음을 데모로 보여준다.