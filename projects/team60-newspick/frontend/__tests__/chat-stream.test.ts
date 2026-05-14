import { describe, expect, it } from "vitest";
import { startChatStream, type EventSourceLike } from "../components/chat/chat-stream";

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

describe("startChatStream", () => {
  it("chat_stream_accumulates_token_events_into_assistant_message", () => {
    const fakeEventSource = new FakeEventSource();
    const snapshots: string[] = [];

    const stream = startChatStream({
      eventSourceFactory: () => fakeEventSource,
      message: "hi",
      onToken: (message) => snapshots.push(message),
    });

    fakeEventSource.emit("token", { text: "안녕" });
    fakeEventSource.emit("token", { text: "하세요" });
    fakeEventSource.emit("done", { articles: [] });

    expect(snapshots).toEqual(["안녕", "안녕하세요"]);
    expect(stream.assistantText).toBe("안녕하세요");
    expect(stream.state).toBe("closed");
    expect(fakeEventSource.closed).toBe(true);
  });
});
