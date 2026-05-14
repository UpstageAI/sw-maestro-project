import { http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { handlers } from "../mocks/handlers";
import { subscribeSse } from "../lib/sse";

type Listener = (event: MessageEvent<string>) => void;

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  listeners = new Map<string, Listener[]>();
  onerror: ((event: Event) => void) | null = null;
  closed = false;
  url: string;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(name: string, listener: Listener) {
    const listeners = this.listeners.get(name) ?? [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }

  close() {
    this.closed = true;
  }

  emit(name: string, data: unknown) {
    this.emitRaw(name, JSON.stringify(data));
  }

  emitRaw(name: string, data: string) {
    const event = new MessageEvent(name, { data });
    this.listeners.get(name)?.forEach((listener) => listener(event));
  }
}

const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  FakeEventSource.instances = [];
  vi.unstubAllGlobals();
});
afterAll(() => server.close());

describe("subscribeSse", () => {
  it("dispatches_named_events_and_closes_on_done", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    const events: Array<[string, unknown]> = [];
    const onDone = vi.fn();

    subscribeSse("http://localhost:8080/api/refresh-stream", {
      onEvent: (event, data) => events.push([event, data]),
      onDone,
    });

    const eventSource = FakeEventSource.instances[0];
    eventSource.emit("step", { step: "collect", current: 1, total: 12 });
    eventSource.emit("done", { articleIds: ["article_001"] });

    expect(events).toEqual([
      ["step", { step: "collect", current: 1, total: 12 }],
      ["done", { articleIds: ["article_001"] }],
    ]);
    expect(onDone).toHaveBeenCalledOnce();
    expect(eventSource.closed).toBe(true);
  });

  it("normalizes_raw_error_events_and_closes", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    const events: Array<[string, unknown]> = [];

    subscribeSse("http://localhost:8080/api/refresh-stream", {
      onEvent: (event, data) => events.push([event, data]),
    });

    const eventSource = FakeEventSource.instances[0];
    eventSource.emitRaw("error", "timeout");

    expect(events).toEqual([
      ["error", { code: "SSE_ERROR", message: "timeout" }],
    ]);
    expect(eventSource.closed).toBe(true);
  });

  it("calls_on_error_for_malformed_non_error_events", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    const onError = vi.fn();

    subscribeSse("http://localhost:8080/api/refresh-stream", {
      onEvent: vi.fn(),
      onError,
    });

    const eventSource = FakeEventSource.instances[0];
    eventSource.emitRaw("step", "not-json");

    expect(onError).toHaveBeenCalledOnce();
    expect(eventSource.closed).toBe(true);
  });

  it("mock_refresh_stream_returns_sse_payload", async () => {
    server.use(http.get("http://unused.test/health", () => new Response(null)));

    const response = await fetch("http://localhost:8080/api/refresh-stream");
    const body = await response.text();

    expect(response.headers.get("content-type")).toContain("text/event-stream");
    expect(body).toContain("event: step");
    expect(body).toContain("event: done");
  });
});
