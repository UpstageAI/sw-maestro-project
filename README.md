# Coin Agent — Testnet Console

Binance Spot Testnet 기반의 암호화폐 모의투자 웹 콘솔입니다. 현재 구현은 수동 주문 테스트와 AI 기반 자연어 자동매매 세션 제어를 모두 포함하며, 모든 데이터와 실행은 백엔드 API를 통해서만 이뤄집니다.

> **주의**: 이 앱은 Binance **Spot Testnet** 전용입니다. 실제 자금은 사용되지 않으며, 프론트엔드는 Binance를 직접 호출하지 않습니다.

## 기술 스택

| 구분 | 기술 |
|---|---|
| UI 프레임워크 | React 19 |
| 빌드 도구 | Vite 8 |
| 언어 | TypeScript 6 (strict) |
| 라우팅 | React Router v7 |
| 서버 상태 관리 | TanStack React Query v5 |
| 차트 | Lightweight Charts v5 |
| 아이콘 | Lucide React |
| 스타일링 | CSS Modules |

## 로컬 실행

### 사전 준비

- Node.js 18 이상
- 백엔드 API 서버가 `http://localhost:8000` 에서 실행 중이어야 합니다.

### 설치 및 실행

```bash
npm install
cp .env.example .env
npm run dev
```

### 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | 백엔드 API 서버 주소 |

### 스크립트

| 명령어 | 설명 |
|---|---|
| `npm run dev` | 개발 서버 실행 |
| `npm run build` | TypeScript 컴파일 + 프로덕션 빌드 |
| `npm run preview` | 빌드 결과 미리보기 |
| `npm run lint` | ESLint 검사 |

## 현재 화면 구성

### 대시보드 (`/dashboard`)

선택한 심볼(`BTCUSDT`, `ETHUSDT`) 기준으로 잔고, 현재가, 호가, 캔들, 백엔드 stream 상태를 확인합니다.

- 현재가 조회
- 호가와 depth 조회 (현재 BE는 depth 5단계 기준)
- 캔들 조회
- 잔고 조회
- stream 상태 카드

### 자연어 자동매매 (`/auto-trading`)

자연어 지시문으로 **백엔드가 소유하는 연속 자동매매 세션**을 시작/중지하고 상태를 확인하는 화면입니다.

- `POST /api/v1/testnet/orders/auto/session/start` 호출로 세션 시작
- `POST /api/v1/testnet/orders/auto/session/stop` 호출로 세션 중지 요청
- `GET /api/v1/testnet/orders/auto/session` polling 으로 session 상태 확인
- 현재 세션의 tick interval, tick count, selected trader, latest run, latest report 표시
- `runId` 기준으로 Reports 화면 이동 가능

중요한 구현 제약:

- 클라이언트는 로컬 루프를 돌리지 않습니다.
- 최종 주문 실행과 재검증 권한은 항상 BE에 있습니다.
- 세션은 `REPORT_READY`, `NO_ORDER`, 일부 재시도 가능한 `HOLD` 에서만 계속 진행됩니다.
- agentic run resume 는 현재 지원되지 않습니다.

### 주문 테스트 (`/orders`)

수동 구조화 주문 테스트 화면입니다.

- 시장가/지정가 주문 생성
- 특정 주문 상태 조회
- 특정 주문 취소
- 최근 run 로그 표시
- `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT` 에 대한 resume UI 제공

### 에이전트 리포트 (`/reports`)

`runId` 기준의 단일 실행 리포트를 조회합니다.

- `GET /api/v1/testnet/orders/report?runId=...` 기반 live report 조회
- 의사결정 trace, hold reason, reason codes, 실행 결과 확인
- cadence/history 전용 API는 아직 없으므로 placeholder 표시

### 환경 설정 (`/settings`)

설정 화면은 현재 **설명용/placeholder 중심**입니다.

- 현재 연결된 API base URL 표시
- API 키는 서버 환경 변수로 관리됨을 안내
- BE의 `GET /api/v1/testnet/config` endpoint 는 존재하지만, 현재 FE는 이를 live 호출해 표시하지 않습니다.

## 구현 경계 요약

- FE는 Binance를 직접 호출하지 않습니다.
- AI가 주문을 직접 실행하는 것처럼 보이면 안 됩니다.
- `READY_FOR_BE` 는 실행 완료가 아니라 **BE 재검증 대기**를 의미합니다.
- 오류 응답은 현재 snake_case, 성공 응답은 camelCase 를 사용합니다.
