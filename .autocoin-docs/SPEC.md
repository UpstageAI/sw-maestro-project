# Coin Agent 제품 명세

## 문서 목적

이 문서는 Binance Spot Testnet 전용 Coin Agent의 제품 범위와 수용 기준을 정의한다. 대상은 가상 자금 기반 현물 주문 테스트이며, 실거래 기능은 포함하지 않는다.

## 1. 제품 목표

사용자가 다음 흐름을 안전하게 검증할 수 있어야 한다.

- 계정 잔고 조회
- Testnet 연결 설정 조회
- 시세, 호가, 캔들 조회
- 현물 주문 테스트 요청
- run 상태 확인과 필요 시 resume
- run report 조회
- 주문 상태 조회
- 주문 취소
- WebSocket 시세 상태 확인

핵심 목표는 단순 주문 제출이 아니라, 주문 전 판단과 주문 후 결과를 `runId` 단위로 추적 가능한 테스트 경험을 제공하는 것이다.

## 2. 범위

### 포함 범위

- Binance Spot Testnet 전용 연동
- 현물 `MARKET`, `LIMIT` 주문 테스트
- 주문 생성 전 AI 기반 판단과 BE 재검증
- `POST /api/v1/testnet/orders` run 중심 응답
- `POST /api/v1/testnet/orders/resume` 공개 재개 API
- `GET /api/v1/testnet/config` 공개 설정 조회 API
- `GET /api/v1/testnet/orders/report` 공개 run report 조회 API
- 주문 상태 조회와 주문 취소의 분리된 API
- 단계별 trace와 상태값 기반 설명

### 제외 범위

- Binance Production 사용
- 선물, 마진, 레버리지, 출금
- 브라우저에서 Binance 직접 호출
- AI의 직접 주문 제출, 직접 서명, 직접 정책 완화
- 미구현 설정 관리 API를 완료된 기능처럼 취급하는 문서화

## 3. 대상 사용자

- 로컬 환경에서 Spot Testnet 주문 흐름을 검증하려는 사용자
- FE, BE, AI 책임 경계를 명확히 실험하려는 개발자
- 정책 기반 hold, resume, rejection 흐름을 데모하고 싶은 팀

## 4. 핵심 사용자 시나리오

### US-01 시세와 잔고 확인

사용자는 주문 전 잔고, 현재가, 호가, 캔들을 조회할 수 있어야 한다.

### US-01A Testnet 설정 확인

사용자는 현재 서버가 사용하는 Testnet REST, WebSocket Stream, WebSocket API 기준 URL을 조회할 수 있어야 한다.

### US-02 주문 테스트 시작

사용자는 `POST /api/v1/testnet/orders` 로 주문 테스트를 시작하고, Binance 원본 응답이 아니라 run 중심 응답을 받아야 한다.

### US-03 보류 후 재개

사용자는 `HOLD` 응답을 받은 뒤 같은 `runId` 로 `POST /api/v1/testnet/orders/resume` 를 호출해 흐름을 이어갈 수 있어야 한다.

### US-04 상태 조회와 취소

사용자는 주문 생성과 별개로 `GET /api/v1/testnet/orders/status`, `DELETE /api/v1/testnet/orders` 를 사용해 상태 조회와 취소를 수행할 수 있어야 한다.

### US-05 리포트와 추적

사용자는 최소한 `runId`, `lifecycleStatus`, `holdReason`, `reasonCodes` 수준의 결과를 확인할 수 있어야 하며, 추후 화면이나 저장 계층에서 상세 trace를 조회할 수 있어야 한다.

현재 구현 기준에서 run report는 공개 BE API와 FE Reports 페이지 양쪽에 live 연동되어 있다. 다만 cadence/history 전용 API는 아직 없어 placeholder 상태다.

## 5. 기능 요구사항

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| FR-01 | 시스템은 Binance Spot Testnet만 사용해야 한다. | Production URL과 키를 사용하지 않는다. |
| FR-02 | FE는 Binance를 직접 호출하지 않아야 한다. | 모든 외부 호출이 BE 공개 API를 경유한다. |
| FR-03 | 시스템은 잔고 조회를 제공해야 한다. | `GET /api/v1/testnet/account` 가 정규화 응답을 반환한다. |
| FR-03A | 시스템은 Testnet 연결 설정 조회를 제공해야 한다. | `GET /api/v1/testnet/config` 가 REST/WS 기준 URL을 camelCase 응답으로 반환한다. |
| FR-04 | 시스템은 가격, 호가, 캔들 조회를 제공해야 한다. | `ticker/price`, `ticker/book`, `klines` 가 동작한다. |
| FR-05 | 주문 생성 API는 run 중심 응답을 반환해야 한다. | `POST /api/v1/testnet/orders` 가 `runId`, `lifecycleStatus` 를 포함한다. |
| FR-06 | 주문 생성 API는 Binance 원본 응답을 public contract로 사용하지 않아야 한다. | 직접 `clientOrderId`, `transactTime`, `origQty` 전체를 canonical 성공 계약으로 문서화하지 않는다. |
| FR-07 | 시스템은 공개 resume API를 제공해야 한다. | `POST /api/v1/testnet/orders/resume` 가 public contract에 포함된다. |
| FR-08 | 주문 상태 조회와 주문 취소는 별도 API로 제공해야 한다. | `GET /orders/status`, `DELETE /orders` 가 유지된다. |
| FR-08A | 시스템은 run report 조회를 제공해야 한다. | `GET /api/v1/testnet/orders/report` 가 `runId` 기준 report payload를 반환한다. |
| FR-09 | AI는 별도 HTTP 서비스로 동작해야 한다. | `/runs/start`, `/runs/resume`, `/runs/complete` 가 존재한다. |
| FR-10 | AI run 저장소의 현재 구현 특성을 문서화해야 한다. | 로컬 JSON 파일 기반 저장소임을 명시한다. |
| FR-11 | resume 시 이전 이력은 보존되어야 한다. | `resume_history`, 이전 trace 스냅샷 보존 의미가 문서화된다. |
| FR-12 | resume 후 현재 stage trace는 재계산될 수 있어야 한다. | 현재 trace overwrite 특성이 문서화된다. |
| FR-13 | BE만 실행 권한을 가져야 한다. | Binance 제출, 서명, 최종 판정은 BE만 수행한다. |
| FR-14 | 성공 응답 명명은 camelCase여야 한다. | `runId`, `lifecycleStatus`, `holdReason`, `reasonCodes` 를 사용한다. |
| FR-15 | 현재 오류 응답 명명은 snake_case여야 한다. | `error_code`, `request_id` 를 사용한다. |
| FR-16 | FE Reports 현재 상태를 사실대로 명시해야 한다. | `runId` 기준 live report 조회와 cadence/history placeholder 상태를 문서화한다. |
| FR-17 | FE Settings config 조회 현재 상태를 사실대로 명시해야 한다. | pending 또는 미구현으로 문서화한다. |

## 6. 비기능 요구사항

- 안전성: fail-closed가 기본값이어야 한다.
- 일관성: 루트 문서 간 상태값과 필드명이 같아야 한다.
- 추적성: 주문 run은 `runId` 로 식별 가능해야 한다.
- 설명 가능성: `HOLD`, `NO_ORDER`, `BE_REJECTED` 를 구분해 설명해야 한다.
- 권한 분리: FE 입력, AI 판단, BE 실행 권한이 섞이면 안 된다.

## 7. canonical 상태 의미

- `HOLD`: 추가 승인 또는 추가 데이터가 필요하다.
- `NO_ORDER`: 신규 주문을 만들지 않고 종료한다.
- `READY_FOR_BE`: AI 관점 통과, BE 재검증 대기다.
- `BE_REJECTED`: AI 이후 BE가 최종 차단했다.
- `REPORT_READY`: 제출 또는 차단 결과까지 포함한 run 보고가 준비됐다.
- `FAILED`: 기술 실패 또는 복구 불가 상태다.

## 8. 현재 UI 성숙도 메모

- 주문 생성 플로우는 run 중심 계약을 향하고 있다.
- 주문 상태 조회와 취소는 separate API 흐름으로 동작한다.
- 리포트 화면은 현재 `runId` 기준 live report 조회 단계다.
- 설정 화면은 현재 placeholder 단계지만, BE의 config 조회 endpoint 자체는 구현되어 있다.
- Reports 화면은 현재 BE의 run report 조회 endpoint와 연결되어 있다. 다만 cadence/history 전용 API는 아직 없다.

이 성숙도 차이는 제품 요구사항의 축소가 아니라, 현재 구현 단계의 차이로 해석한다.
