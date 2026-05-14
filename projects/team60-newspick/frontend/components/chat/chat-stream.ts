import { apiUrl } from "../../lib/api/base";

export type ChatArticleSummary = {
  id: string;
  title: string;
  source: string;
  publishedAt: string;
};

export type EventSourceLike = {
  addEventListener: (name: string, listener: (event: MessageEvent<string>) => void) => void;
  close: () => void;
  onerror: ((event: Event) => void) | null;
};

type ChatStreamState = "open" | "closed" | "error";

type ChatStreamOptions = {
  eventSourceFactory?: (url: string) => EventSourceLike;
  message: string;
  onDone?: (articles: ChatArticleSummary[]) => void;
  onError?: (message: string) => void;
  onToken?: (message: string) => void;
};

function defaultEventSourceFactory(url: string): EventSourceLike {
  return new EventSource(url);
}

function parseEventData<T>(event: MessageEvent<string>): T | null {
  try {
    return JSON.parse(event.data) as T;
  } catch {
    return null;
  }
}

function buildChatStreamUrl(message: string) {
  const params = new URLSearchParams({ q: message });

  return apiUrl(`/api/chat-stream?${params.toString()}`);
}

export function startChatStream({
  eventSourceFactory = defaultEventSourceFactory,
  message,
  onDone,
  onError,
  onToken,
}: ChatStreamOptions) {
  let assistantText = "";
  let state: ChatStreamState = "open";
  const eventSource = eventSourceFactory(buildChatStreamUrl(message));

  const close = (nextState: ChatStreamState) => {
    if (state !== "open") {
      return;
    }

    state = nextState;
    eventSource.close();
  };

  eventSource.addEventListener("token", (event) => {
    const data = parseEventData<{ text?: string }>(event);
    const token = data?.text ?? "";

    if (!token) {
      return;
    }

    assistantText += token;
    onToken?.(assistantText);
  });

  eventSource.addEventListener("done", (event) => {
    const data = parseEventData<{ articles?: ChatArticleSummary[] }>(event);
    onDone?.(data?.articles ?? []);
    close("closed");
  });

  eventSource.addEventListener("error", (event) => {
    const data = parseEventData<{ message?: string }>(event);
    onError?.(data?.message ?? "답변 생성 실패");
    close("error");
  });

  eventSource.onerror = () => {
    onError?.("답변 생성 실패");
    close("error");
  };

  return {
    close: () => close("closed"),
    get assistantText() {
      return assistantText;
    },
    get state() {
      return state;
    },
  };
}
