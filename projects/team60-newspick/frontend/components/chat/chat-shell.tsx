"use client";

import Link from "next/link";
import { FormEvent, KeyboardEvent } from "react";
import { useChatStore } from "../../lib/store/chat";
import { ChatArticleCards } from "./chat-article-cards";
import type { EventSourceLike } from "./chat-stream";
import { MarkdownMessage } from "./markdown-message";

type ChatShellProps = {
  streamFactory?: (url: string) => EventSourceLike;
  suggestions?: string[];
};

export function ChatShell({ streamFactory, suggestions = [] }: ChatShellProps) {
  const draft = useChatStore((state) => state.draft);
  const errorMessage = useChatStore((state) => state.errorMessage);
  const isPending = useChatStore((state) => state.isPending);
  const threadMessages = useChatStore((state) => state.threadMessages);
  const setDraft = useChatStore((state) => state.setDraft);
  const submitChat = useChatStore((state) => state.submit);
  const resetChat = useChatStore((state) => state.reset);

  const canSubmit = draft.trim().length > 0 && !isPending;
  const hasMessages = threadMessages.length > 0;
  const canReset = hasMessages || Boolean(errorMessage);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submitChat(streamFactory);
  };

  const handleInputKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    event.preventDefault();
    submitChat(streamFactory);
  };

  return (
    <aside
      aria-label="AI 뉴스 채팅"
      className="flex h-full min-h-0 flex-col bg-bg"
      role="complementary"
    >
      <header className="flex items-center justify-between border-b border-line bg-surface px-[18px] py-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-500">
            <svg
              aria-hidden="true"
              className="h-[18px] w-[18px]"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path d="M12 2a8 8 0 0 1 8 8c0 5-8 12-8 12S4 15 4 10a8 8 0 0 1 8-8z" />
              <circle cx="12" cy="10" r="2.5" fill="currentColor" stroke="none" />
            </svg>
          </span>
          <div>
            <p className="m-0 text-[15px] font-[700] leading-[1.3] text-ink">AI 어시스턴트</p>
            <p className="m-0 text-[11px] font-[500] text-hint">기사·리포트 검색</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {canReset ? (
            <button
              aria-label="새 대화"
              className="grid h-[34px] w-[34px] shrink-0 place-items-center rounded-full border border-line bg-surface text-hint active:bg-bg active:text-ink"
              onClick={resetChat}
              type="button"
            >
              <svg
                aria-hidden="true"
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.8}
                viewBox="0 0 20 20"
              >
                <path d="M15.5 4.5A7.5 7.5 0 1 1 5.5 14" />
                <path d="M5 10V5.5H9.5" />
              </svg>
            </button>
          ) : null}
          <Link
            aria-label="채팅 닫기"
            className="grid h-[34px] w-[34px] shrink-0 place-items-center rounded-full border border-line bg-surface text-hint active:bg-bg active:text-ink"
            href="/feed"
          >
            <svg
              aria-hidden="true"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.8}
              viewBox="0 0 20 20"
            >
              <path d="m5 5 10 10" />
              <path d="m15 5-10 10" />
            </svg>
          </Link>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5">
        {!hasMessages ? (
          <div className="m-auto flex flex-col items-center gap-2 text-center">
            <div className="mb-1 h-14 w-14">
              <svg aria-hidden="true" className="h-full w-full" fill="none" viewBox="0 0 40 40">
                <circle cx="20" cy="20" fill="#fff0e7" r="20" />
                <path
                  d="M12 20c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8"
                  stroke="#ff8a3d"
                  strokeLinecap="round"
                  strokeWidth="2"
                />
                <circle cx="20" cy="20" fill="#ff8a3d" r="2.5" />
              </svg>
            </div>
            <p className="m-0 text-[16px] font-[700] text-ink">뉴스가 궁금하면 물어보세요</p>
            <p className="m-0 text-[13px] font-[500] leading-[1.6] text-hint">
              수집한 기사와 리포트를 바탕으로
              <br />
              답변을 드릴게요.
            </p>
            {suggestions.length > 0 ? (
              <div className="mt-1 flex flex-wrap justify-center gap-2">
                {suggestions.map((suggestion) => (
                  <button
                    className="rounded-[20px] border border-line bg-surface px-3.5 py-2 text-[13px] font-[500] leading-[1.3] text-ink active:border-brand-500/30 active:bg-brand-50 active:text-brand-500"
                    key={suggestion}
                    onClick={() => setDraft(suggestion)}
                    type="button"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {threadMessages.map((message) => (
              <div
                className={`flex items-end gap-2 ${
                  message.role === "user" ? "flex-row-reverse" : ""
                }`}
                key={message.id}
              >
                {message.role === "assistant" ? (
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brand-500 text-[9px] font-[800] tracking-[0.3px] text-white">
                    AI
                  </span>
                ) : null}
                {message.status === "pending" ? (
                  <div
                    aria-label="답변 생성 중"
                    className="flex min-w-14 items-center gap-1 rounded-[18px] rounded-bl bg-surface px-4 py-3.5 shadow-[0_1px_4px_rgba(25,31,40,0.07)]"
                    role="status"
                  >
                    <span className="h-[7px] w-[7px] rounded-full bg-hint" />
                    <span className="h-[7px] w-[7px] rounded-full bg-hint" />
                    <span className="h-[7px] w-[7px] rounded-full bg-hint" />
                  </div>
                ) : (
                  <div
                    className={`max-w-[82%] rounded-[18px] px-3.5 py-[11px] text-[14px] leading-[1.55] break-keep ${
                      message.role === "user"
                        ? "rounded-br bg-brand-500 text-white"
                        : "rounded-bl bg-surface text-ink shadow-[0_1px_4px_rgba(25,31,40,0.07)]"
                    }`}
                  >
                    {message.role === "assistant" ? (
                      <MarkdownMessage text={message.text} />
                    ) : (
                      <p className="m-0 whitespace-pre-wrap">{message.text}</p>
                    )}
                    {message.role === "assistant" && message.articles ? (
                      <ChatArticleCards articles={message.articles} />
                    ) : null}
                  </div>
                )}
              </div>
            ))}
            {errorMessage ? (
              <div
                className="rounded-[18px] rounded-bl border border-line bg-surface px-3.5 py-[11px] text-[14px] font-[600] leading-[1.55] text-muted shadow-[0_1px_4px_rgba(25,31,40,0.07)]"
                role="alert"
              >
                {errorMessage}
              </div>
            ) : null}
          </div>
        )}
      </div>

      <form
        className="flex shrink-0 items-center gap-2 border-t border-line bg-surface px-3.5 pb-3.5 pt-2.5"
        onSubmit={handleSubmit}
      >
        <label className="sr-only" htmlFor="chat-input">
          메시지 입력
        </label>
        <textarea
          className="h-[42px] flex-1 resize-none rounded-[21px] border border-line bg-bg px-3.5 py-2.5 text-[14px] leading-[1.4] text-ink outline-none focus:border-brand-500/40 focus:bg-surface"
          id="chat-input"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder="궁금한 뉴스를 물어보세요"
          rows={1}
          value={draft}
        />
        <button
          aria-label="보내기"
          className="grid h-[42px] w-[42px] shrink-0 place-items-center rounded-full bg-brand-500 text-white disabled:bg-line disabled:text-hint"
          disabled={!canSubmit}
          type="submit"
        >
          <svg aria-hidden="true" className="h-[18px] w-[18px]" fill="none" viewBox="0 0 20 20">
            <path d="M17 10 3 4l3 6-3 6 14-6z" fill="currentColor" />
          </svg>
        </button>
      </form>
    </aside>
  );
}
