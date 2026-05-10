# Coin Agent 테스트 및 데모 기준

## 문서 목적

이 문서는 현재 구현을 기준으로 어떤 흐름을 검증해야 하는지 정의한다. 목적은 happy path만 확인하는 것이 아니라, run 중심 분기와 책임 경계를 재현하는 것이다.

## 1. 테스트 원칙

- 모든 테스트는 Binance Spot Testnet 기준으로 수행한다.
- FE는 Binance를 직접 호출하지 않는다.
- AI는 Binance를 직접 제출하거나 서명하지 않는다.
- BE만 실행 권한을 가진다는 점을 반드시 검증한다.
- `POST /api/v1/testnet/orders` 는 raw order response가 아니라 run response로 검증한다.

## 2. 핵심 계약 테스트

| ID | 대상 | 검증 포인트 |
|---|---|---|
| T-00 | `GET /api/v1/testnet/config` | Testnet 기준 URL을 camelCase로 반환하는지 |
| T-01 | `POST /api/v1/testnet/orders` | `runId`, `lifecycleStatus` 중심 응답 여부 |
| T-02 | `POST /api/v1/testnet/orders` | `HOLD`, `NO_ORDER`, `BE_REJECTED`, `REPORT_READY` 분기 |
| T-03 | `POST /api/v1/testnet/orders/resume` | hold run 재개 가능 여부 |
| T-04 | `GET /api/v1/testnet/orders/status` | 주문 상태 조회가 생성 API와 분리되어 있는지 |
| T-04A | `GET /api/v1/testnet/orders/report` | `runId` 기준 report 조회가 가능한지 |
| T-05 | `DELETE /api/v1/testnet/orders` | 주문 취소가 생성 API와 분리되어 있는지 |
| T-06 | 오류 응답 | `error_code`, `request_id` snake_case 유지 여부 |
| T-07 | 성공 응답 | camelCase 필드 유지 여부 |
| T-08 | AI service | `/runs/start`, `/runs/resume`, `/runs/complete` 동작 여부 |
| T-09 | AI resume | 이전 이력 보존과 현재 trace overwrite 특성 검증 |
| T-10 | FE maturity | Reports live 조회 + cadence/history placeholder, Settings 미연동 상태가 사실대로 반영되는지 |

## 3. 백엔드 API 체크리스트

- `GET /health` 응답 확인
- `GET /api/v1/testnet/account` 응답 확인
- `GET /api/v1/testnet/config` 응답 확인
- `GET /api/v1/testnet/ticker/price` 응답 확인
- `GET /api/v1/testnet/ticker/book` 응답 확인
- `GET /api/v1/testnet/klines` 응답 확인
- `POST /api/v1/testnet/orders` 응답이 run 중심인지 확인
- `POST /api/v1/testnet/orders/resume` 응답이 run 중심인지 확인
- `GET /api/v1/testnet/orders/status` 응답 확인
- `GET /api/v1/testnet/orders/report` 응답 확인
- `DELETE /api/v1/testnet/orders` 응답 확인
- `GET /api/v1/testnet/stream/status` 응답 확인

## 4. 필수 시나리오

### S-01 READY_FOR_BE 후 제출 성공

1. 주문 요청 전송
2. AI가 `READY_FOR_BE` 반환
3. BE 재검증 통과
4. Binance 제출
5. 최종 `REPORT_READY` 또는 제출 결과 포함 응답 확인

### S-02 HOLD_REVIEW_REQUIRED 후 resume

1. 주문 요청 전송
2. `HOLD` 와 `holdReason=HOLD_REVIEW_REQUIRED` 확인
3. 같은 `runId` 로 `POST /orders/resume` 호출
4. 이후 `READY_FOR_BE`, `BE_REJECTED`, `REPORT_READY` 중 적절한 분기 확인

### S-03 HOLD_DATA_INSUFFICIENT 후 resume

1. 데이터 부족 상태 유도
2. `HOLD` 와 `holdReason=HOLD_DATA_INSUFFICIENT` 확인
3. 보완 입력 후 같은 `runId` 로 resume
4. 새 판단 결과 확인

### S-04 AI 통과 후 BE 차단

1. AI가 `READY_FOR_BE` 반환
2. BE deterministic 재검증 실패 유도
3. `BE_REJECTED` 와 `reasonCodes` 확인

### S-05 주문 상태 조회와 취소 분리

1. 주문 생성 이후 `GET /orders/status` 로 상태 확인
2. 별도 `DELETE /orders` 로 취소 수행
3. 생성 응답 계약과 조회, 취소 계약이 서로 다름을 확인

## 5. AI resume 특화 검증

검증해야 할 사실:

- `request_context` 는 유지된다.
- `resume_history` 는 누적된다.
- `decision_trace_history` 는 이전 trace 스냅샷을 저장한다.
- 새 resume 후 현재 `decision_trace` 는 재계산된 값으로 바뀔 수 있다.
- 새 resume 후 현재 `verificationChecks` 도 재계산 결과로 overwrite 될 수 있다.
- 같은 로컬 run store 파일을 유지하는 한 프로세스 재시작 이후에도 non-agentic run resume 가 가능한지 확인한다.

이 부분은 문서와 구현이 어긋나기 쉬운 지점이므로 반드시 명시적으로 검증한다.

## 6. FE 확인 항목

### Orders

- 생성 응답을 raw order success만으로 해석하지 않는지 확인
- `runId`, `lifecycleStatus`, `holdReason`, `reasonCodes` 소비 계획이 문서와 맞는지 확인

### Reports

- `runId` 기준 live report 조회가 연결된 상태임을 확인
- cadence/history 는 아직 placeholder 상태임을 확인
- BE report API 존재와 FE의 현재 화면 성숙도를 구분해서 발표하도록 확인

### Settings

- BE config endpoint 존재와 FE 미연동 상태를 구분해서 확인
- placeholder 문구가 현재 상태를 숨기지 않는지 확인

## 7. 데모 메시지 기준

데모에서는 다음 문장을 일관되게 유지한다.

- FE는 Binance를 직접 호출하지 않는다.
- AI는 실행 권한자가 아니다.
- `POST /orders` 는 run 응답을 반환한다.
- `POST /orders/resume` 는 hold run을 이어가기 위한 public endpoint다.
- `GET /config` 와 `GET /orders/report` 는 BE에 존재하지만, FE의 Settings/Reports 연동 상태와 동일한 말이 아니다.
- Reports는 현재 `runId` 기준 live report 조회가 연결되어 있고, cadence/history 는 placeholder 상태다.
- Settings 화면 연동은 아직 pending 이다.

## 8. 합격 기준

- 루트 문서 간 상태명과 필드명이 일치한다.
- 생성 API가 raw Binance 응답 계약으로 서술되지 않는다.
- resume endpoint가 빠지지 않는다.
- config endpoint와 run report endpoint 상태가 문서 간 일치한다.
- FE, BE, AI 권한 경계가 흔들리지 않는다.
- 현재 미구현 영역이 구현 완료처럼 보이지 않는다.
