# Coin Agent Frontend 구현 체크리스트

> Binance Spot Testnet 전용 React Frontend 구현 진행 상황을 추적한다.

## 0. 프로젝트 초기 설정

- [x] Vite + React + TypeScript 프로젝트 생성
- [x] 디자인 시스템 토큰 (색상, 타이포그래피, 간격) 설정
- [x] CSS Module 기반 스타일링 구조 설정
- [x] 폴더 구조 정의 (pages, components, api, types, hooks, constants)
- [x] 라우터 설정 (`/settings`, `/dashboard`, `/orders`, `/reports`)
- [x] API 클라이언트 모듈 설정 (base URL 분리, 환경변수 기반)
- [x] 공통 타입 정의 (BalanceSnapshot, PriceSnapshot, SpotOrderRequest 등)
- [x] 공통 UI 컴포넌트 (Button, Card, Badge, Banner, Spinner, Skeleton, EmptyState)

## 1. 환경 설정 페이지 (`/settings`) — FR-01

- [x] `EnvironmentCard` 컴포넌트 구현
  - [x] Testnet REST/WS base URL 읽기 전용 표시
  - [x] 서버 환경 변수 설정 상태 표시 (설정됨/미설정)
  - [x] API Key 원문 입력/표시 금지
  - [x] 실거래 URL이 아님을 경고 배너로 항상 노출
- [ ] 설정 상태 조회 API 연동 (현재 placeholder 유지)

## 2. 대시보드 페이지 (`/dashboard`) — FR-02, FR-03, FR-04, FR-05, FR-10

### 2.1 잔고 조회 — FR-02

- [x] `BalanceCard` 컴포넌트 구현
  - [x] `asset`, `free`, `locked` 표시
  - [x] 로딩/빈 상태/성공/오류 상태 처리
- [x] `GET /api/v1/testnet/account` 연동

### 2.2 현재가 조회 — FR-03

- [x] `PriceCard` 컴포넌트 구현
  - [x] `symbol`, `price` 표시
  - [x] 심볼 선택 (BTCUSDT, ETHUSDT)
- [x] `GET /api/v1/testnet/ticker/price` 연동

### 2.3 호가 조회 — FR-04

- [x] `OrderBookCard` 컴포넌트 구현
  - [x] bids / asks depth snapshot 표시
  - [x] lastUpdateId 표시
- [x] `GET /api/v1/testnet/ticker/book` 연동

### 2.4 캔들 조회 — FR-05

- [x] `KlineChart` 컴포넌트 구현
  - [x] OHLCV 캔들스틱 차트 시각화 (lightweight-charts)
  - [x] interval 선택 (1m 기본)
- [x] `GET /api/v1/testnet/klines` 연동

### 2.5 WebSocket 시세 수신 — FR-10

- [x] `StreamStatusCard` 컴포넌트 구현
  - [x] stream name, latest event 표시
  - [x] 연결 상태 (수신 중/연결 중/재연결 중/연결 끊김) 표시
  - [x] WebSocket 연결 실패 시 수동 조회 fallback 안내
- [x] WebSocket 연결 관리 hook 구현 (`useStreamStatus` 폴링 hook)

## 3. 주문 테스트 페이지 (`/orders`) — FR-06, FR-07, FR-08, FR-09

### 3.1 현물 매수/매도 주문 — FR-06, FR-07

- [x] `OrderForm` 컴포넌트 구현
  - [x] 주문 타입 선택 (MARKET / LIMIT)
  - [x] 방향 선택 (BUY / SELL)
  - [x] 시장가 매수: `quoteOrderQty` 입력
  - [x] 시장가 매도: `quantity` 입력
  - [x] 지정가 주문: `price`, `quantity`, `timeInForce` 입력
  - [x] 필수 파라미터 모두 채워져야 주문 버튼 활성화
  - [x] 주문 타입에 맞지 않는 파라미터 조합 사전 차단
  - [x] Testnet 주문임을 명확히 표시
- [x] `POST /api/v1/testnet/orders` 연동
- [x] 주문 결과 즉시 로그 영역 표시

### 3.2 주문 상태 조회 — FR-08

- [x] `OrderStatusPanel` 컴포넌트 구현
  - [x] `orderId` 또는 `origClientOrderId` 입력
  - [x] `status`, `executedQty` 등 상태 표시
  - [x] 주문 상태 배지 (NEW, FILLED, CANCELED, REJECTED)
- [x] `GET /api/v1/testnet/orders/status` 연동

### 3.3 주문 취소 — FR-09

- [x] `CancelOrderPanel` 컴포넌트 구현
  - [x] `symbol`, `orderId` 또는 `origClientOrderId` 입력
  - [x] 유효한 값일 때만 취소 요청 가능
  - [x] 취소 전 확인 다이얼로그
  - [x] 취소 결과 표시
- [x] `DELETE /api/v1/testnet/orders` 연동

## 4. 리포트/로그 페이지 (`/reports`) — FR-13~FR-21

### 4.1 주문 테스트 이력

- [x] 최근 주문 테스트 이력 시간순 표시
- [x] 실패 원인 및 Binance 에러 코드 표시

### 4.2 Agent 상태 표시

- [x] `run_id` 디버그/로그 영역 확인 가능
- [x] `decision_trace` 단계 카드 구분 표시
  - [x] Policy/Planning 단계 (policy retrieval 근거 요약)
  - [x] Risk 단계 (`reasonCodes`, trace 근거)
  - [x] Evaluator 단계
  - [x] Execution 단계
  - [x] Run Summary
- [x] `PASS` 배지에 "BE 재검증 대기" 설명 함께 표시

### 4.3 Agent 상태별 UI 처리

- [x] `NO_ORDER` — 차단 사유, `reason_codes`, 입력 수정 CTA
- [x] `HOLD` + `HOLD_REVIEW_REQUIRED` — 승인 필요 배지, 승인/거절 CTA
- [x] `HOLD` + `HOLD_DATA_INSUFFICIENT` — 데이터 부족 설명, 재조회/재입력 CTA
- [x] `BE_REJECTED` — AI 통과 후 BE 차단 설명, 상세 사유 보기
- [x] `FAILED` — 기술 실패 원인, 재시도 가능 여부

### 4.4 리포트 cadence 표시

- [x] 단일 `run_id` 기준 리포트 조회
- [x] cadence/history 미지원 시 placeholder 안내 표시
- [ ] cadence 이벤트 시간순 표시 (전용 API 추가 후 구현)
- [ ] `HOLD` 후 resume 시 같은 `run_id` 안에서 이어 붙여 표시 (전용 API 추가 후 구현)

## 5. 공통 UI/UX 요구사항

- [x] 상단에 "Binance Spot Testnet" 문구 항상 표시
- [x] 실거래가 아님을 배너로 명확히 표시
- [x] stream 이름 소문자, REST 심볼 대문자 일관성
- [x] 수익 보장/공격적 투자 표현 미사용
- [x] 숫자 문자열 정규화 표시 + 원본 값 확인 가능
- [x] 로딩 → 스켈레톤/Spinner
- [x] 빈 상태 → 시작 가이드 표시
- [x] 성공 → 카드/차트/표
- [x] 부분 오류 → 오류 배너 + 마지막 정상 데이터
- [x] 전체 오류 → 재시도 안내 + Testnet 경고

## 6. AI-oriented UI/UX

- [x] AI Agent 작업 상태 표시 (대기/처리 중/응답 생성 중/완료/실패)
- [ ] AI 응답 streaming 중 미완성 표시 (BE 대기)
- [x] AI 설명과 시스템 원본 결과 라벨 분리
- [x] AI 응답이 주문 실행 여부 결정처럼 보이지 않도록 처리
- [x] AI 응답 실패 시 fallback 메시지 제공
- [x] Agent 다단계 수행 시 현재 단계 표시

## 7. MVP 완료 기준

- [x] Spot Testnet Key 설정 상태 확인 가능
- [x] 잔고 조회 화면 동작 (API 연동은 BE 대기)
- [x] 가격/호가/캔들 조회 화면 동작 (API 연동은 BE 대기)
- [x] Spot 매수/매도 주문 테스트 화면 동작 (API 연동은 BE 대기)
- [x] 주문 상태 조회 화면 동작 (API 연동은 BE 대기)
- [x] 주문 취소 화면 동작 (API 연동은 BE 대기)
- [x] WebSocket 시세 수신 화면 동작 (API 연동은 BE 대기)
- [x] 실거래 엔드포인트 사용 0건
- [x] AI run 상태 추적 UI 동작

## 8. API 연동 준비 현황 (BE 개발 완료 후)

> `VITE_API_BASE_URL` 환경 변수만 설정하면 즉시 API 연동 테스트 가능

- [x] `GET /api/v1/testnet/account` — 잔고 조회
- [x] `GET /api/v1/testnet/ticker/price` — 현재가 조회
- [x] `GET /api/v1/testnet/ticker/book` — 호가 조회
- [x] `GET /api/v1/testnet/klines` — 캔들 조회
- [ ] `POST /api/v1/testnet/orders` — 주문 생성
- [x] `GET /api/v1/testnet/orders/status` — 주문 상태 조회
- [x] `DELETE /api/v1/testnet/orders` — 주문 취소
- [x] `GET /api/v1/testnet/stream/status` — WebSocket 상태 확인
