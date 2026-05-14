# 상태 관리

상태를 두 종류로 분리한다.

| 종류 | 라이브러리 | 용도 |
|---|---|---|
| 클라이언트 상태 | **Zustand** | UI 상태, 사용자 선택값, SSE 수신 진행률 등 |
| 서버 상태 | **TanStack Query** | API GET 응답 캐싱·리페치·로딩 상태 |

## Zustand 사용처

| store | 데이터 |
|---|---|
| `useCategoryStore` | 온보딩에서 선택한 카테고리 배열 |
| `useChatStore` | 챗 대화 히스토리 (메모리, 새로고침 시 초기화) |
| `useRefreshStore` | 홈 SSE 진행률 (`{ collect: {current, total}, summarize: {current, total}, status }`) |

> 인증 없음 정책으로 세션 UUID 도 발급하지 않는다 — `userId` 관련 store 는 만들지 않음.

### 예시

```ts
// lib/store/category.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

type CategoryState = {
  selected: string[];
  toggle: (cat: string) => void;
  setAll: (cats: string[]) => void;
};

export const useCategoryStore = create<CategoryState>()(
  persist(
    (set) => ({
      selected: [],
      toggle: (cat) =>
        set((state) => ({
          selected: state.selected.includes(cat)
            ? state.selected.filter((c) => c !== cat)
            : [...state.selected, cat],
        })),
      setAll: (cats) => set({ selected: cats }),
    }),
    { name: "newspick-category" }
  )
);
```

> 카테고리만 `persist`(localStorage). 챗·진행률 같은 휘발 상태는 persist 빼고 메모리만.

## TanStack Query 사용처

| query | 엔드포인트 | 캐시 키 |
|---|---|---|
| `useFeed` | `GET /api/feed` | `["feed"]` |
| `useArticle` | `GET /api/articles/{id}` | `["article", id]` |
| `useReportToday` | `GET /api/report/today` | `["report", "today"]` |

SSE 엔드포인트(`/api/refresh-stream`, `/api/chat-stream`)는 TanStack Query 로 다루지 않는다 — 이벤트 스트림은 [frontend/sse-client.md](sse-client.md) 의 `EventSource` 헬퍼로 처리.

### 셋업

```tsx
// app/providers.tsx
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,        // 1분
        refetchOnWindowFocus: false,
      },
    },
  }));
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

```tsx
// app/layout.tsx 안에서 <Providers> 로 감싼다
```

### 페이지에서 사용

```tsx
// app/(app)/feed/page.tsx
"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchFeed } from "@/lib/api";

export default function FeedPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["feed"],
    queryFn: fetchFeed,
  });

  if (isLoading) return <FeedLoading />;
  if (error) return <FeedError />;
  return <NewsList articles={data!.articles} />;
}
```

## 의존성

```bash
pnpm add zustand @tanstack/react-query
```

## 상태 분리 원칙

- 서버에서 받은 데이터는 **TanStack Query 만** 보관. Zustand 에 복사하지 않는다 (단일 진실원천).
- 클라이언트만의 상태(UI 토글, 입력값 등)는 **Zustand 또는 컴포넌트 local state**.
- SSE 수신값은 **Zustand** (여러 컴포넌트가 구독, 컴포넌트 unmount 후에도 진행률 유지).

## 주의점

- TanStack Query 는 `staleTime: 0` 기본인데 그러면 매번 재요청. MVP 시연에서는 불필요한 호출을 줄이기 위해 1분 정도 둔다.
- Zustand `persist` 는 SSR 환경에서 hydration mismatch 위험 — 클라이언트 컴포넌트에서만 접근.
- 카테고리 변경 UX 는 MVP 범위 밖이므로 ([product/ux-decisions.md](../product/ux-decisions.md)), 한 번 선택 후 수정 UI 는 만들지 않는다.

## 레퍼런스

- Zustand: https://github.com/pmndrs/zustand
- TanStack Query: https://tanstack.com/query/latest
