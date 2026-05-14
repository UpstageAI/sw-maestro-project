"use client";

import { Bot, Loader2 } from "lucide-react";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { useScrollToBottom } from "@/hooks/useScrollToBottom";
import type { ThreadMessage } from "@/lib/knowledgeChat";

type Props = {
  messages: ThreadMessage[];
  isAwaitingAnswer?: boolean;
};

export function ChatContainer({ messages, isAwaitingAnswer }: Props) {
  const scrollRef = useScrollToBottom<HTMLDivElement>([
    messages.length,
    isAwaitingAnswer,
  ]);

  return (
    <div
      ref={scrollRef}
      className="chat-scroll flex-1 overflow-y-auto bg-slate-50/60 px-4 py-6 sm:px-6"
    >
      <div className="mx-auto flex max-w-3xl flex-col gap-5">
        {messages.length === 0 && !isAwaitingAnswer ? (
          <p className="text-center text-sm text-slate-500">
            아래에 질문을 입력하면 지식 베이스(RAG)를 참고해 답변합니다.
          </p>
        ) : null}
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {isAwaitingAnswer ? (
          <div className="flex gap-3" aria-live="polite" aria-busy="true">
            <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-900 text-white">
              <Bot className="h-4 w-4" />
            </span>
            <div className="flex items-center gap-2 rounded-2xl rounded-tl-md bg-white px-4 py-3 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
              <Loader2 className="h-4 w-4 animate-spin text-slate-500" />
              답변을 불러오는 중…
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
