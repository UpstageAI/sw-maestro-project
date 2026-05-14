# Next.js

## 사용 범위

- 모든 사용자 화면 ([design.md](../design.md) §4 의 11개 화면).
- API Route 는 **사용하지 않는다** — 백엔드는 Spring 단일 출처. Next.js 는 순수 프론트.
- 데이터 페칭은 대부분 클라이언트에서 TanStack Query 로 ([state-management.md](state-management.md)). SSR 의존도는 낮음(시연용 SPA 성격).

## 버전·언어

| 항목 | 값 |
|---|---|
| Next.js | 15.x |
| React | 19.x (Next 15 기본) |
| TypeScript | strict 모드 |
| 패키지 매니저 | pnpm |

## 디렉토리 구조

App Router 기반.

```
frontend/
├── app/
│   ├── layout.tsx              # 루트 레이아웃 (폰트, 공통 head)
│   ├── globals.css             # Tailwind v4 base + 커스텀 토큰
│   ├── page.tsx                # 스플래시 (NewPick + 서비스 시작하기)
│   ├── onboarding/
│   │   └── category/page.tsx   # 카테고리 선택
│   ├── (app)/                  # 메인 앱 그룹 (하단 네비 공유)
│   │   ├── layout.tsx          # phone-frame + bottom-nav
│   │   ├── feed/page.tsx       # 홈 피드 (로딩/완료 분기)
│   │   ├── article/[id]/page.tsx
│   │   ├── report/page.tsx
│   │   └── chat/page.tsx
│   └── _components/            # 공용 UI (BottomNav, PhoneFrame 등)
├── lib/
│   ├── api.ts                  # Spring API fetcher
│   ├── sse.ts                  # EventSource 헬퍼
│   └── store/                  # Zustand stores
├── public/
│   └── newspick.png            # prototype/assets/newspick.png 이전
├── tailwind.config.ts          # (v4 의 경우 CSS @theme 으로 대체)
├── next.config.ts
├── tsconfig.json
└── package.json
```

> `app/` 안에 라우트가 아닌 보조 폴더는 `_components/` 처럼 언더스코어 prefix 로 두면 라우트로 인식되지 않는다.

## 라우팅·렌더링 전략

- **Server Component 기본**: 페이지 컴포넌트는 가능하면 RSC. 데이터 fetch 는 서버에서 한 번 끝내고 props 로 내림.
- **Client Component**: 인터랙션·SSE·Zustand 사용 부분만 `'use client'`.
- **SSG vs SSR**: 모든 페이지가 사용자 로컬 백엔드와 통신하므로 SSG 의미 없음. dev 모드 SSR 만.
- **Route Handler (`app/api/*`)** 는 **사용하지 않는다** — 모든 API 호출은 Spring 8080 으로 직접.

## 페이지별 렌더링 전략

| 라우트 | 형태 | 이유 |
|---|---|---|
| `/` (스플래시) | RSC | 정적 마크업만 |
| `/onboarding/category` | Client | 카테고리 선택 인터랙션, Zustand 저장 |
| `/(app)/feed` | Client | SSE 진행률 + TanStack Query |
| `/(app)/article/[id]` | Client | 인라인 퀴즈 인터랙션 |
| `/(app)/report` | RSC + Client island | 헤더 정적, 데이터는 클라이언트 fetch |
| `/(app)/chat` | Client | SSE 토큰 스트림 |

## 환경 변수

`.env.local` (gitignore):

```
NEXT_PUBLIC_API_BASE=http://localhost:8080
```

> Solar / LangSmith API 키는 **절대로** Next.js 에 두지 않는다. 키가 필요한 호출은 Spring 또는 Python 만 한다.

## 시작 명령

```bash
pnpm install
pnpm dev          # http://localhost:3000
pnpm build && pnpm start  # 빌드 후 프로덕션 모드 (시연 직전 권장)
```

## 주의점

- prototype 의 `script.js` 동작은 Next.js 의 라우팅·`useState` 로 자연스럽게 분해됨. iOS-frame.jsx 는 시각 레퍼런스용으로만 보존, 본 앱에는 [design.md](../design.md) §3.1 의 가벼운 `phone-frame` 만 구현.
- 시연 환경(노트북) 변경에 대비해 모든 호스트 설정은 환경변수로. 하드코딩된 `localhost:8080` 노출 X.
- React 19 의 `useFormStatus`, `use` 같은 신기능은 우선 도입 보류 — 안정성 우선.

## 레퍼런스

- Next.js 15 docs: https://nextjs.org/docs
- React 19 release notes: https://react.dev/blog
