# llm-blind-date-frontend

[llm-blind-date](../llm-blind-date) 프론트엔드. AI 페르소나 기반 소개팅 시뮬레이션의 사용자 인터페이스.

협업 원칙은 [`AGENTS.md`](AGENTS.md).

## Stack
- **Next.js 16** (App Router) / React 19
- **TypeScript 5**
- **Tailwind CSS 4**
- **TanStack Query 5** — 캐시 + `/api/jobs/{id}` 폴링
- **openapi-fetch + openapi-typescript** — 백엔드 OpenAPI 자동 동기화

## Setup

```bash
pnpm install
cp .env.example .env.local             # NEXT_PUBLIC_API_BASE_URL 확인
pnpm dev                               # http://localhost:3000
```

백엔드(`../llm-blind-date`)를 먼저 띄우면 OpenAPI에서 타입을 갱신할 수 있습니다:

```bash
pnpm typegen                           # → src/lib/api/types.ts 갱신
```

## Layout

```
src/
├── app/                  # Next.js App Router
├── lib/
│   ├── api/
│   │   ├── client.ts     # 단일 fetch 진입점 (openapi-fetch + unwrap)
│   │   └── types.ts      # 자동 생성 — 손대지 말 것
│   └── queries/
│       └── QueryProvider.tsx
└── components/
```

## Scripts
| 명령 | 설명 |
|---|---|
| `pnpm dev` | 개발 서버 (Turbopack) |
| `pnpm build` | 프로덕션 빌드 |
| `pnpm start` | 프로덕션 실행 |
| `pnpm lint` | ESLint |
| `pnpm typegen` | 백엔드 OpenAPI → `src/lib/api/types.ts` (백엔드 실행 필수) |

## Backend Contract
- 백엔드 레포: `../llm-blind-date/`
- CORS: 백엔드가 `http://localhost:3000` 허용 — 포트 바꾸지 말 것
- 에러 포맷: `{"detail": "..."}` (`lib/api/client.ts` 의 `unwrap` 가 `ApiError` 로 변환)
- API 명세: `../llm-blind-date/docs/backend-specs/02-api-specification.md`
