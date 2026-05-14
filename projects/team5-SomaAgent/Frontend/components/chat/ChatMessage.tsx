import { Bot } from "lucide-react";
import { ActionResultBanner } from "@/components/chat/ActionResultBanner";
import { MentoringCardList } from "@/components/chat/MentoringCardList";
import { SourceList } from "@/components/chat/SourceList";
import { knowledgeSourcesToUiSources } from "@/lib/knowledgeSourceToUi";
import { knowledgeMentoringSourcesToCards } from "@/lib/knowledgeToMentoring";
import type { ThreadMessage } from "@/lib/knowledgeChat";

export function ChatMessage({ message }: { message: ThreadMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
          {message.text}
        </div>
      </div>
    );
  }

  if (message.role === "assistant" && message.kind === "error") {
    return (
      <div className="flex gap-3">
        <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-900 text-white">
          <Bot className="h-4 w-4" />
        </span>
        <div className="max-w-[82%] rounded-2xl rounded-tl-md border border-red-200 bg-red-50 px-4 py-3 text-sm leading-relaxed text-red-800 shadow-sm">
          {message.message}
        </div>
      </div>
    );
  }

  if (message.role === "assistant" && message.kind === "knowledge") {
    const uiSources = knowledgeSourcesToUiSources(message.sources);
    const mentoringCards = knowledgeMentoringSourcesToCards(message.sources);
    return (
      <div className="flex gap-3">
        <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-900 text-white">
          <Bot className="h-4 w-4" />
        </span>
        <div className="flex w-full max-w-[82%] flex-col gap-3">
          <div className="space-y-2 rounded-2xl rounded-tl-md bg-white px-4 py-3 text-sm leading-relaxed text-slate-800 shadow-sm ring-1 ring-slate-200">
            <p className="whitespace-pre-wrap">{message.answer}</p>
            <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2 text-[11px] text-slate-500">
              <span>
                {message.llm_used ? "LLM 요약 사용" : "검색 결과 기반 (LLM 미사용)"}
              </span>
              {message.llm_error ? (
                <span className="text-amber-700">LLM: {message.llm_error}</span>
              ) : null}
            </div>
          </div>
          {mentoringCards.length > 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ring-1 ring-slate-100">
              <p className="mb-3 text-xs font-medium text-slate-600">
                멘토링 후보 — 출처의{" "}
                <code className="rounded bg-slate-100 px-1 text-[11px]">source_id</code>가
                숫자인 항목만 신청 버튼이 활성화됩니다.
              </p>
              <MentoringCardList
                items={mentoringCards}
                applyMode="openapi_mentoring"
              />
            </div>
          ) : null}
          {uiSources.length > 0 ? <SourceList sources={uiSources} /> : null}
        </div>
      </div>
    );
  }

  if (message.role === "agent" && message.kind === "action_result") {
    return (
      <div className="flex gap-3">
        <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-900 text-white">
          <Bot className="h-4 w-4" />
        </span>
        <div className="flex w-full max-w-[82%] flex-col gap-2">
          {message.results.map((result, index) => (
            <ActionResultBanner
              key={`${result.actionType}-${result.status}-${index}`}
              result={result}
            />
          ))}
        </div>
      </div>
    );
  }

  return null;
}
