import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ChatShell } from "../../components/chat/chat-shell";
import type { ChatArticleSummary, EventSourceLike } from "../../components/chat/chat-stream";
import articleCardSummarySchema from "../../../docs/contracts/json-schemas/article-card-summary.json";

const requiredArticleCardFields = articleCardSummarySchema.required;

type Listener = (event: MessageEvent<string>) => void;

class FakeEventSource implements EventSourceLike {
  listeners = new Map<string, Listener[]>();
  onerror: ((event: Event) => void) | null = null;
  closed = false;

  addEventListener(name: string, listener: Listener) {
    const listeners = this.listeners.get(name) ?? [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }

  close() {
    this.closed = true;
  }

  emit(name: string, data: unknown) {
    const event = new MessageEvent(name, { data: JSON.stringify(data) });
    this.listeners.get(name)?.forEach((listener) => listener(event));
  }
}

function expectMatchesArticleCardSummary(value: unknown) {
  expect(value !== null && typeof value === "object").toBe(true);
  const record = value as Record<string, unknown>;

  for (const field of requiredArticleCardFields) {
    expect(record[field], `${field} is required`).not.toBeUndefined();
  }

  expect(typeof record.id).toBe("string");
  expect((record.id as string).length).toBeGreaterThan(0);
  expect(typeof record.title).toBe("string");
  expect((record.title as string).length).toBeGreaterThan(0);
  expect(typeof record.source).toBe("string");
  expect((record.source as string).length).toBeGreaterThan(0);
  expect(typeof record.publishedAt).toBe("string");
  expect(Number.isNaN(Date.parse(record.publishedAt as string))).toBe(false);
}

const fixtureUserMessage = "오픈AI 오늘 소식 알려줘";
const fixtureTokens = ["오픈AI는 ", "오늘 의료 분야 진출을 발표했습니다."];
const fixtureArticles: ChatArticleSummary[] = [
  {
    id: "article_001",
    title: "오픈AI 의료 분야 진출 본격화",
    source: "테크크런치",
    publishedAt: "2026-05-13T08:00:00Z",
  },
  {
    id: "article_002",
    title: "AI 의료 진단 정확도 90% 돌파",
    source: "한경 IT",
    publishedAt: "2026-05-13T09:30:00Z",
  },
];

type SseEvent = { name: string; data: string };

async function readSseEventsUntilDone(reader: ReadableStreamDefaultReader<Uint8Array>, timeoutMs: number) {
  const decoder = new TextDecoder();
  const events: SseEvent[] = [];
  let buffer = "";
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    let separator = buffer.indexOf("\n\n");
    while (separator !== -1) {
      const chunk = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 2);

      let eventName = "message";
      let eventData = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event: ")) {
          eventName = line.slice("event: ".length).trim();
        } else if (line.startsWith("data: ")) {
          eventData += line.slice("data: ".length);
        }
      }
      if (eventName !== "message" || eventData.length > 0) {
        events.push({ name: eventName, data: eventData });
      }
      separator = buffer.indexOf("\n\n");
    }

    if (events.some((event) => event.name === "done") || events.some((event) => event.name === "error")) {
      break;
    }
  }

  return events;
}

async function runLiveChatStreamContractIfEnabled() {
  if (process.env.RUN_LIVE_CONTRACT !== "true") {
    return;
  }

  const feBaseUrl = process.env.FE_BASE_URL ?? "http://localhost:3000";
  const beBaseUrl = process.env.BE_BASE_URL ?? "http://localhost:8080";
  const aiBaseUrl = process.env.AI_BASE_URL ?? "http://localhost:8000";

  expect(() => new URL(feBaseUrl)).not.toThrow();
  expect(() => new URL(beBaseUrl)).not.toThrow();
  expect(() => new URL(aiBaseUrl)).not.toThrow();

  const response = await fetch(`${beBaseUrl}/api/chat-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: fixtureUserMessage, contextArticleIds: [] }),
  });
  expect(response.ok, `BE /api/chat-stream responded with ${response.status}`).toBe(true);
  expect(response.body).not.toBeNull();

  const reader = response.body!.getReader();
  let events: SseEvent[] = [];
  try {
    events = await readSseEventsUntilDone(reader, 10000);
  } finally {
    await reader.cancel().catch(() => undefined);
  }

  const tokenEvents = events.filter((event) => event.name === "token");
  const doneEvents = events.filter((event) => event.name === "done");
  expect(tokenEvents.length).toBeGreaterThanOrEqual(1);
  expect(doneEvents).toHaveLength(1);
  expect(events.indexOf(tokenEvents[0])).toBeLessThan(events.indexOf(doneEvents[0]));

  const donePayload = JSON.parse(doneEvents[0].data) as { articles?: unknown[] };
  const articles = donePayload.articles ?? [];
  for (const article of articles) {
    expectMatchesArticleCardSummary(article);
  }
}

afterEach(() => cleanup());

describe("chat stream contract", () => {
  it("chat_stream_contract_fixture_and_live_mode_use_article_card_summary", async () => {
    const fakeEventSource = new FakeEventSource();

    render(
      <ChatShell streamFactory={() => fakeEventSource} suggestions={[]} />,
    );

    fireEvent.change(screen.getByRole("textbox", { name: "메시지 입력" }), {
      target: { value: fixtureUserMessage },
    });
    fireEvent.click(screen.getByRole("button", { name: "보내기" }));

    expect(screen.getByText(fixtureUserMessage)).toBeTruthy();
    expect(screen.getByRole("status", { name: "답변 생성 중" })).toBeTruthy();

    act(() => {
      for (const text of fixtureTokens) {
        fakeEventSource.emit("token", { text });
      }
    });

    const accumulated = fixtureTokens.join("");
    expect(screen.getByText(accumulated)).toBeTruthy();

    act(() => {
      fakeEventSource.emit("done", { articles: fixtureArticles });
    });

    expect(screen.queryByRole("status", { name: "답변 생성 중" })).toBeNull();
    expect(fakeEventSource.closed).toBe(true);

    const referenceList = screen.getByRole("list", { name: "참고 기사" });
    expect(referenceList).toBeTruthy();

    for (const article of fixtureArticles) {
      expectMatchesArticleCardSummary(article);
      expect(screen.getByText(article.title)).toBeTruthy();
      expect(screen.getByText(article.source)).toBeTruthy();
    }

    await runLiveChatStreamContractIfEnabled();
  });
});
