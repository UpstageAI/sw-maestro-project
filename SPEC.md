# Coin Agent 제품 명세

## 문서 목적

이 문서는 현재 구현 기준의 제품 범위와 수용 기준을 정의한다. 대상은 Binance Spot Testnet 전용 수동 주문 테스트와 자연어 자동매매 세션 제어다.

## 1. 제품 목표

사용자가 다음 흐름을 안전하게 검증할 수 있어야 한다.

- 잔고 조회
- Testnet 연결 설정 조회 API 보유
- 현재가 / 호가 / 캔들 조회
- 수동 주문 run 시작과 resume
- 자연어 auto order 1회 실행
- 자연어 auto-trading session start / stop / status
- run report 조회
- 주문 상태 조회와 취소
- stream 상태 확인

## 2. 포함 범위

- Binance Spot Testnet 전용 연동
- 현물 `MARKET`, `LIMIT` 주문 테스트
- 수동 run 기반 주문 흐름
- 자연어 agentic auto order
- backend-owned continuous auto session
- live snapshot 기반 auto-trading 재평가
- run/report/checkpoint 저장

## 3. 제외 범위

- Binance Production
- 선물, 마진, 레버리지, 출금
- FE의 Binance 직접 호출
- AI의 Binance 직접 제출/서명
- agentic same-run resume
- cadence/history 전용 FE API

## 4. 현재 핵심 사용자 시나리오

### US-01 시세와 잔고 확인

Dashboard에서 잔고, 현재가, 호가, 캔들, stream 상태 확인

### US-02 수동 주문 테스트

Orders 화면에서 수동 구조화 주문을 제출하고 `runId` 기반 상태를 확인

### US-03 hold run 재개

수동 HOLD 응답을 받은 뒤 `POST /orders/resume` 로 재개

### US-04 자연어 auto order 1회 실행

`POST /orders/auto` 로 자연어 주문 해석 결과와 run 상태 확인

### US-05 자연어 자동매매 세션 제어

`/auto-trading` 에서 자연어 지시문으로 연속 세션 시작/중지, tick 상태, latest run/report 확인

## 5. 기능 요구사항

| ID | 요구사항 |
|---|---|
| FR-01 | 시스템은 Binance Spot Testnet만 사용해야 한다. |
| FR-02 | FE는 Binance를 직접 호출하지 않아야 한다. |
| FR-03 | 수동 주문 생성 API는 run 중심 응답을 반환해야 한다. |
| FR-04 | hold run resume API를 제공해야 한다. |
| FR-05 | 자연어 auto order API를 제공해야 한다. |
| FR-06 | 연속 auto-trading session start / stop / status API를 제공해야 한다. |
| FR-07 | auto-trading loop는 FE가 아니라 BE가 소유해야 한다. |
| FR-08 | auto tick은 live account/market snapshot 기반으로 AI를 호출해야 한다. |
| FR-09 | AI는 `/runs/start`, `/runs/agentic/start`, `/runs/resume`, `/runs/complete` HTTP surface를 가져야 한다. |
| FR-10 | Reports는 `runId` 기준 live report 조회가 가능해야 한다. |
| FR-11 | Settings는 아직 placeholder 중심이라는 현재 성숙도를 숨기지 않아야 한다. |

## 6. 현재 제약 메모

- agentic run resume 는 현재 미지원
- auto session 은 single active session 모델
- FE Reports는 cadence/history placeholder 유지
- auto session continuation 은 일부 retryable HOLD에서만 허용

## 7. 수용 기준

- 문서가 현재 구현된 route / API / 상태값 / 제약을 사실대로 설명한다.
- 수동 주문과 자연어 auto-trading session 흐름이 분리되어 설명된다.
- BE만 최종 실행 권한을 가진다는 사실이 흔들리지 않는다.
