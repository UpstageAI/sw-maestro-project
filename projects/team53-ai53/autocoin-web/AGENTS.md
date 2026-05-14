# Coin Agent Frontend — Code Convention (AGENTS.md)

> 이 문서는 Coin Agent Frontend 프로젝트의 코드 컨벤션을 정의한다.
> `.gemini/styleguide.md`의 리뷰 기준을 따르며, 디자인 시스템은 `DESIGN.md`와 `SKILL.md`를 기준으로 한다.

---

## 1. 기술 스택

| 영역 | 기술 | 비고 |
|---|---|---|
| Framework | React 19 | SPA, Vite 번들러 |
| Language | TypeScript (strict) | `any` 사용 금지 |
| Styling | CSS Modules (`*.module.css`) | 전역 CSS는 reset/font/variable에 한정 |
| Routing | React Router v7 | `/settings`, `/dashboard`, `/orders`, `/reports` |
| Server State | TanStack Query (@tanstack/react-query) | 서버 데이터 캐시, 로딩/에러 상태 관리 |
| Client State | React 내장 (useState, useReducer) + Zustand (전역 필요 시) | 서버 상태와 UI 상태 분리 |
| HTTP Client | fetch wrapper | BE 엔드포인트만 호출 |
| Design System | Agentic (DESIGN.md) | primary=#FF5701, surface=#FFFFFF |

---

## 2. 폴더 구조

```
src/
├── api/            # API 호출 함수 (BE 엔드포인트만)
├── components/
│   ├── common/     # 공통 UI (Button, Card, Badge, Banner, Spinner, Skeleton)
│   └── domain/     # 도메인 컴포넌트 (BalanceCard, OrderForm 등)
├── constants/      # 상수, 엔드포인트, 열거값
├── hooks/          # 커스텀 hooks
├── pages/          # 페이지 컴포넌트 (Settings, Dashboard, Orders, Reports)
├── types/          # TypeScript 타입 정의
├── styles/         # 전역 CSS, CSS variables, reset
└── utils/          # 유틸 함수
```

---

## 3. 네이밍 규칙

| 대상 | 규칙 | 예시 |
|---|---|---|
| 컴포넌트 파일 | PascalCase | `BalanceCard.tsx` |
| CSS Module 파일 | 컴포넌트와 동일 | `BalanceCard.module.css` |
| hook 파일 | camelCase, `use` prefix | `useWebSocket.ts` |
| API 함수 파일 | camelCase | `testnetApi.ts` |
| 타입 파일 | camelCase | `order.ts` |
| 상수 파일 | camelCase | `endpoints.ts` |
| CSS Module import | `styles` 고정 | `import styles from './X.module.css'` |

---

## 4. 컴포넌트 규칙

- 하나의 컴포넌트는 하나의 명확한 책임을 가진다.
- 공통 UI 컴포넌트(`components/common/`)와 도메인 컴포넌트(`components/domain/`)를 분리한다.
- 컴포넌트 이름은 역할을 명확히 드러낸다.
- props가 5개를 초과하면 props 객체화 또는 컴포넌트 분리를 검토한다.
- 리스트 렌더링 시 index를 key로 사용하지 않고, 안정적인 식별자를 사용한다.
- 컴포넌트 내부에 API 호출 로직을 직접 포함하지 않고, hooks 또는 api 모듈로 분리한다.

---

## 5. 상태 관리 규칙

- 서버/API 상태(잔고, 시세, 주문)와 클라이언트 UI 상태(입력값, 모달, 탭)를 분리한다.
- 파생 가능한 값은 중복 저장하지 않는다.
- 심볼 변경 시 이전 심볼 기준 데이터가 stale 상태로 남지 않도록 초기화한다.
- stream 상태와 REST 조회 상태를 분리한다.
- API 실패 후 이전 성공 데이터가 현재 데이터처럼 보이지 않도록 처리한다.

---

## 6. Effect 및 비동기 처리 규칙

- `useEffect`는 외부 시스템과의 동기화가 필요한 경우에만 사용한다.
- 단순 계산이나 파생값 생성에 `useEffect`를 사용하지 않는다.
- API 호출, WebSocket 연결, timer, event listener는 cleanup을 반드시 포함한다.
- 시세 자동 갱신은 기본 동작이 아니며, 수동 조회 버튼 기반 흐름을 우선한다.
- WebSocket 연결은 컴포넌트 unmount 또는 심볼 변경 시 정리한다.

---

## 7. TypeScript 규칙

- 핵심 데이터 구조는 명시적 타입으로 정의한다.
- `any` 사용을 금지한다.
- API 응답 타입과 화면 표시용 타입을 구분한다.
- 주문 상태, 방향, 타입 등 제한된 값은 union type으로 관리한다.
- Binance 응답의 숫자 문자열은 타입에서도 `string`으로 유지하되, 표시 시 정규화한다.

---

## 8. API 호출 규칙

- FE는 Binance API를 직접 호출하지 않는다. 모든 호출은 BE 엔드포인트를 통해 수행한다.
- API 호출 로직은 `src/api/` 모듈에 분리한다.
- base URL은 환경 변수(`VITE_API_BASE_URL`)로 관리한다.
- 모든 API 호출에 로딩/성공/빈 상태/부분 오류/전체 오류를 구분한다.
- API 실패 시 Binance 에러 코드를 함께 표시한다.

---

## 9. 스타일링 규칙

- 스타일링은 CSS Module 방식을 따른다. (`*.module.css`)
- 전역 CSS는 reset, font, CSS variable, body 스타일에 한정한다.
- 인라인 스타일 사용을 지양한다.
- 반복되는 색상, 간격, radius, typography 값은 CSS variable로 관리한다.
- className은 시각적 형태보다 역할과 의미를 기준으로 작성한다.

### 디자인 토큰 (DESIGN.md 기준)

| Token | Value | 용도 |
|---|---|---|
| `--color-primary` | `#FF5701` | 주요 액션, 강조 |
| `--color-secondary` | `#F6F6F1` | 배경, 보조 영역 |
| `--color-success` | `#16A34A` | 성공 상태 |
| `--color-warning` | `#D97706` | 경고 상태 |
| `--color-danger` | `#DC2626` | 위험/오류 상태 |
| `--color-surface` | `#FFFFFF` | 카드/패널 배경 |
| `--color-text` | `#111827` | 본문 텍스트 |
| `--font-primary` | `Playfair Display` | 제목, 본문 |
| `--font-mono` | `JetBrains Mono` | 코드, 라벨 |
| `--spacing-sm` | `8px` | 좁은 간격 |
| `--spacing-md` | `16px` | 기본 간격 |
| `--radius-sm` | `4px` | 작은 라운딩 |
| `--radius-md` | `8px` | 기본 라운딩 |

---

## 10. 안전 규칙

- API Key/Secret을 클라이언트 코드에 포함하지 않는다.
- FE는 API Key 원문을 입력받거나 표시하지 않는다.
- 실거래 URL 문자열(`api.binance.com`, `stream.binance.com`)을 사용하지 않는다.
- 환경 변수 상태는 설정 여부만 표시한다.
- 모든 화면에 "Binance Spot Testnet" 환경임을 명시한다.
- 수익 보장, 투자 권유, 공격적 투자 표현을 사용하지 않는다.

---

## 11. AI-oriented UI/UX 규칙

- AI 응답 streaming 중/완료를 시각적으로 구분한다.
- AI 설명은 시스템 원본 결과와 별도 라벨로 분리한다.
- AI가 주문 실행 여부를 결정하는 것처럼 보이지 않도록 한다.
- `PASS` 배지는 "BE 재검증 대기" 설명과 함께 표시한다.
- Agent 다단계 수행 시 현재 단계를 표시한다.
- AI 응답 실패 시 fallback 메시지를 제공한다.

---

## 12. Blocking 코드 리뷰 대상

다음 항목은 반드시 수정 요청한다:

1. FE에서 Binance API를 직접 호출하는 코드
2. API Key/Secret이 클라이언트 코드에 포함된 코드
3. 실거래로 오해될 수 있는 문구 또는 화면
4. 주문 필수 파라미터 검증 없이 주문 요청을 보내는 코드
5. 주문 실패를 성공처럼 표시하는 코드
6. `any`로 핵심 API 응답이나 주문 타입을 처리하는 코드
7. CSS Module을 사용하지 않고 전역 스타일을 남발하는 코드
8. AI 응답이 주문 실행 결정처럼 보이는 UI
