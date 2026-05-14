"use client";

import { FormEvent, useState } from "react";
import { GenerateResponse, sendRevisionMessage } from "../lib/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type RevisionChatProps = {
  onDocumentUpdate: (document: GenerateResponse["document"]) => void;
};

export function RevisionChat({ onDocumentUpdate }: RevisionChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isPending, setIsPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isPending) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsPending(true);

    try {
      const response = await sendRevisionMessage(trimmed);
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.assistant_message,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      onDocumentUpdate(response.document);
    } catch (error) {
      const fallback: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "응답을 받지 못했어요. 백엔드가 아직 준비되지 않았거나 네트워크 문제일 수 있어요. 잠시 후 다시 시도해주세요.",
      };
      setMessages((prev) => [...prev, fallback]);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <section className="chat no-print">
      <header className="chatHeader">
        <h2>명세서 다듬기</h2>
        <p className="chatHint">
          예: &ldquo;청구항 1번을 더 황당하게 바꿔줘&rdquo;, &ldquo;배경기술을
          두 문장으로 줄여줘&rdquo;
        </p>
      </header>

      <ol className="chatLog" aria-live="polite">
        {messages.length === 0 ? (
          <li className="chatEmpty">
            아직 대화가 없습니다. 아래 입력창에 수정 요청을 자연어로 적어보세요.
          </li>
        ) : (
          messages.map((msg) => (
            <li key={msg.id} className={`chatMessage chatMessage--${msg.role}`}>
              <span className="chatRole">
                {msg.role === "user" ? "나" : "AI"}
              </span>
              <p>{msg.content}</p>
            </li>
          ))
        )}
        {isPending ? (
          <li className="chatMessage chatMessage--assistant chatMessage--pending">
            <span className="chatRole">AI</span>
            <p>응답 작성 중&hellip;</p>
          </li>
        ) : null}
      </ol>

      <form className="chatComposer" onSubmit={onSubmit}>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          rows={2}
          placeholder="수정하고 싶은 부분을 자연어로 적어보세요"
          disabled={isPending}
        />
        <button type="submit" disabled={isPending || input.trim().length === 0}>
          {isPending ? "응답 대기 중..." : "보내기"}
        </button>
      </form>
    </section>
  );
}
