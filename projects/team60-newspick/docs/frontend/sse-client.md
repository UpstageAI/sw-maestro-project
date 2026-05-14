# SSE 클라이언트

## 사용 범위

- **홈 로딩 진행률**: `EventSource('/api/refresh-stream')`
- **AI 챗 스트리밍**: `EventSource('/api/chat-stream?q=...')`

## 라이브러리

브라우저 내장 **`EventSource`** 만 사용. `@microsoft/fetch-event-source` 같은 보강 라이브러리는 도입하지 않는다 (인증 없음 정책 → 헤더 커스터마이즈 불요).

## 헬퍼

`lib/sse.ts` 에 공통 래퍼 정의:

```ts
type SseHandlers<T> = {
  onEvent: (event: string, data: T) => void;
  onDone?: () => void;
  onError?: (err: Event) => void;
};

export function subscribeSse<T>(url: string, handlers: SseHandlers<T>) {
  const es = new EventSource(url);

  // 이름이 명시된 이벤트들만 따로 listener 등록
  ["step", "warn", "token", "done", "error"].forEach((name) => {
    es.addEventListener(name, (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        if (name === "done") {
          handlers.onEvent("done", data);
          handlers.onDone?.();
          es.close();
        } else {
          handlers.onEvent(name, data);
        }
      } catch (err) {
        console.error("SSE parse error", err);
      }
    });
  });

  es.onerror = (err) => {
    handlers.onError?.(err);
    es.close();
  };

  return () => es.close();
}
```

## 홈 진행률 연동

DOM 직접 조작이 아닌 Zustand store 갱신:

```tsx
// app/(app)/feed/page.tsx (발췌)
"use client";
import { useEffect } from "react";
import { useRefreshStore } from "@/lib/store/refresh";
import { subscribeSse } from "@/lib/sse";

export default function FeedPage() {
  const setStep = useRefreshStore((s) => s.setStep);
  const setStatus = useRefreshStore((s) => s.setStatus);

  useEffect(() => {
    setStatus("loading");
    const close = subscribeSse<{ step: string; current: number; total: number }>(
      `${process.env.NEXT_PUBLIC_API_BASE}/api/refresh-stream`,
      {
        onEvent: (event, data) => {
          if (event === "step") setStep(data.step, data.current, data.total);
          if (event === "warn") console.warn("SSE warn", data);
        },
        onDone: () => setStatus("done"),
        onError: () => setStatus("error"),
      }
    );
    return close;
  }, []);

  // ... loading/done/error 분기 렌더
}
```

> 이벤트 스키마(`step` / `done` / `warn` / `error`)는 [architecture/realtime-ui-states.md](../architecture/realtime-ui-states.md) 참조. Spring 이 Python 의 SSE 를 그대로 프록시하므로 스키마 동일.

## 챗 스트리밍 연동

```tsx
// app/(app)/chat/_components/useChatStream.ts (발췌)
import { useChatStore } from "@/lib/store/chat";
import { subscribeSse } from "@/lib/sse";

export function sendChat(query: string) {
  const append = useChatStore.getState().appendAssistantToken;
  const finish = useChatStore.getState().finishAssistant;

  return subscribeSse<{ token?: string; articles?: unknown[] }>(
    `${process.env.NEXT_PUBLIC_API_BASE}/api/chat-stream?q=${encodeURIComponent(query)}`,
    {
      onEvent: (event, data) => {
        if (event === "token" && data.token) append(data.token);
        if (event === "done") finish(data.articles ?? []);
      },
    }
  );
}
```

## 재연결

`EventSource` 는 네트워크 끊김 시 자동 재연결한다. MVP 에서는 별도 재연결 정책 추가하지 않음.

타임아웃은 서버(Spring)가 120초로 강제한다 ([backend/sse.md](../backend/sse.md)). 클라이언트는 `done` / `error` 받을 때까지 대기.

## 환경 변수

`NEXT_PUBLIC_API_BASE` 가 Spring 베이스 URL. dev 는 `http://localhost:8080`.

## 주의점

- `EventSource` 는 GET 만 지원. POST 로 입력값을 보내야 한다면 `@microsoft/fetch-event-source` 를 별도 도입해야 하지만, 현 MVP 는 query string 으로 충분.
- `addEventListener("message", ...)` 는 **이름 없는 SSE 이벤트** 전용이다. 백엔드가 `event: step` 처럼 이름을 명시해 보내므로 위 헬퍼처럼 이름별로 listener 를 따로 단다.
- 페이지 unmount 시 반드시 `es.close()` (위 헬퍼는 cleanup 함수 반환).

## 레퍼런스

- MDN EventSource: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- 백엔드 SSE 정의: [backend/sse.md](../backend/sse.md)
