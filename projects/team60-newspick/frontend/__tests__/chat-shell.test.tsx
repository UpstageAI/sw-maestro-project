import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChatShell } from "../components/chat/chat-shell";
import type { EventSourceLike } from "../components/chat/chat-stream";
import { useChatStore } from "../lib/store/chat";

type Listener = (event: MessageEvent<string>) => void;

class FakeEventSource implements EventSourceLike {
  listeners = new Map<string, Listener[]>();
  onerror: ((event: Event) => void) | null = null;

  addEventListener(name: string, listener: Listener) {
    const listeners = this.listeners.get(name) ?? [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }

  close() {
    return undefined;
  }

  emit(name: string, data: unknown) {
    const event = new MessageEvent(name, { data: JSON.stringify(data) });
    this.listeners.get(name)?.forEach((listener) => listener(event));
  }
}

function neverEmittingFactory() {
  return () => new FakeEventSource();
}

describe("ChatShell", () => {
  it("chat_shell_renders_empty_state_and_input", () => {
    render(<ChatShell suggestions={["오늘 뉴스 요약해줘"]} />);

    expect(screen.getByRole("complementary", { name: "AI 뉴스 채팅" })).toBeTruthy();
    expect(screen.getByRole("textbox", { name: "메시지 입력" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "보내기" }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByText("오늘 뉴스 요약해줘")).toBeTruthy();
  });

  it("submitting_chat_input_adds_user_message_and_pending_assistant", () => {
    render(<ChatShell streamFactory={neverEmittingFactory()} suggestions={[]} />);

    const input = screen.getByRole("textbox", { name: "메시지 입력" });
    const sendButton = screen.getByRole("button", { name: "보내기" });

    fireEvent.change(input, { target: { value: "오늘 AI 뉴스 알려줘" } });
    expect(sendButton.hasAttribute("disabled")).toBe(false);

    fireEvent.click(sendButton);

    expect(screen.getByText("오늘 AI 뉴스 알려줘")).toBeTruthy();
    expect(screen.getByRole("status", { name: "답변 생성 중" })).toBeTruthy();
    expect(sendButton.hasAttribute("disabled")).toBe(true);
    expect(useChatStore.getState().isPending).toBe(true);
  });

  it("enter_submits_and_shift_enter_keeps_editing", () => {
    render(<ChatShell streamFactory={neverEmittingFactory()} suggestions={[]} />);

    const input = screen.getByRole("textbox", { name: "메시지 입력" });

    fireEvent.change(input, { target: { value: "첫 줄" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
    expect(useChatStore.getState().threadMessages).toHaveLength(0);

    fireEvent.keyDown(input, { key: "Enter" });
    const userMessages = useChatStore
      .getState()
      .threadMessages.filter((message) => message.role === "user");
    expect(userMessages).toHaveLength(1);
    expect(userMessages[0].text).toBe("첫 줄");
  });

  it("chat_stream_error_shows_alert_and_reset_button", () => {
    const fakeEventSource = new FakeEventSource();
    render(<ChatShell streamFactory={() => fakeEventSource} suggestions={[]} />);

    const input = screen.getByRole("textbox", { name: "메시지 입력" });
    fireEvent.change(input, { target: { value: "오늘 AI 뉴스 알려줘" } });
    fireEvent.click(screen.getByRole("button", { name: "보내기" }));

    act(() => {
      fakeEventSource.emit("error", {
        code: "CHAT_STREAM_FAILED",
        message: "답변 생성 실패",
      });
    });

    expect(screen.getByRole("alert").textContent).toContain("답변 생성 실패");
    const resetButton = screen.getByRole("button", { name: "새 대화" });

    fireEvent.click(resetButton);

    expect(screen.queryByText("오늘 AI 뉴스 알려줘")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    expect((screen.getByRole("textbox", { name: "메시지 입력" }) as HTMLTextAreaElement).value).toBe(
      "",
    );
  });

  it("clicking_suggestion_fills_input_without_submit", () => {
    render(<ChatShell suggestions={["AI 관련 핵심 기사 알려줘"]} />);

    fireEvent.click(screen.getByRole("button", { name: "AI 관련 핵심 기사 알려줘" }));

    const input = screen.getByRole("textbox", { name: "메시지 입력" }) as HTMLTextAreaElement;
    expect(input.value).toBe("AI 관련 핵심 기사 알려줘");
    expect(useChatStore.getState().threadMessages).toHaveLength(0);
    expect(screen.getByRole("button", { name: "보내기" }).hasAttribute("disabled")).toBe(false);
  });

  it("chat_shell_renders_assistant_markdown_headings_and_bold", () => {
    const fakeEventSource = new FakeEventSource();
    render(<ChatShell streamFactory={() => fakeEventSource} suggestions={[]} />);

    fireEvent.change(screen.getByRole("textbox", { name: "메시지 입력" }), {
      target: { value: "마크다운 답변 부탁해" },
    });
    fireEvent.click(screen.getByRole("button", { name: "보내기" }));

    act(() => {
      fakeEventSource.emit("token", { text: "## 핵심 요약\n\n**중요**합니다" });
    });

    const heading = screen.getByRole("heading", { name: "핵심 요약" });
    expect(heading).toBeTruthy();
    const strong = screen.getByText("중요");
    expect(strong.tagName.toLowerCase()).toBe("strong");
    expect(screen.queryByText(/##\s*핵심 요약/)).toBeNull();
    expect(screen.queryByText("**중요**합니다")).toBeNull();
  });

  it("chat_shell_keeps_user_message_as_plain_text", () => {
    render(<ChatShell streamFactory={neverEmittingFactory()} suggestions={[]} />);

    fireEvent.change(screen.getByRole("textbox", { name: "메시지 입력" }), {
      target: { value: "**굵게** 보여주지 마" },
    });
    fireEvent.click(screen.getByRole("button", { name: "보내기" }));

    expect(screen.getByText("**굵게** 보여주지 마")).toBeTruthy();
    expect(screen.queryByText("굵게")).toBeNull();
  });

  it("chat_shell_streams_partial_markdown_without_crash", () => {
    const fakeEventSource = new FakeEventSource();
    render(<ChatShell streamFactory={() => fakeEventSource} suggestions={[]} />);

    fireEvent.change(screen.getByRole("textbox", { name: "메시지 입력" }), {
      target: { value: "스트리밍 테스트" },
    });
    fireEvent.click(screen.getByRole("button", { name: "보내기" }));

    expect(() => {
      act(() => {
        fakeEventSource.emit("token", { text: "### 진" });
      });
    }).not.toThrow();

    expect(screen.queryByText("스트리밍 테스트")).toBeTruthy();
  });

  it("chat_thread_survives_unmount_and_remount", () => {
    const fakeEventSource = new FakeEventSource();
    const first = render(
      <ChatShell streamFactory={() => fakeEventSource} suggestions={[]} />,
    );

    fireEvent.change(screen.getByRole("textbox", { name: "메시지 입력" }), {
      target: { value: "탭 이동 후에도 보여야 해" },
    });
    fireEvent.click(screen.getByRole("button", { name: "보내기" }));

    act(() => {
      fakeEventSource.emit("token", { text: "응답 시작" });
    });

    expect(screen.getByText("탭 이동 후에도 보여야 해")).toBeTruthy();
    expect(screen.getByText("응답 시작")).toBeTruthy();

    first.unmount();

    render(<ChatShell streamFactory={() => new FakeEventSource()} suggestions={[]} />);

    expect(screen.getByText("탭 이동 후에도 보여야 해")).toBeTruthy();
    expect(screen.getByText("응답 시작")).toBeTruthy();
  });
});
