"use client";
import { useEffect, useRef, useState } from "react";

type Msg = { role: "user" | "assistant"; content: string; references?: string[]; source?: string };

const SUGGESTIONS = [
  "수습기간 90% 임금 적용이 가능한가요?",
  "주휴수당 받을 수 있는 조건이 뭐예요?",
  "퇴직금은 언제부터 발생하나요?",
  "휴게시간은 어떻게 보장되나요?",
];

export default function QaChat({ contractId }: { contractId: string }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`/api/qa?contractId=${encodeURIComponent(contractId)}`);
        if (!res.ok) return;
        const { logs } = (await res.json()) as { logs: Array<{ question: string; answer: string }> };
        const restored: Msg[] = [];
        for (const l of logs) {
          restored.push({ role: "user", content: l.question });
          if (l.answer) restored.push({ role: "assistant", content: l.answer });
        }
        setMessages(restored);
      } catch { /* ignore */ }
    })();
  }, [contractId]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || loading) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);
    try {
      const res = await fetch("/api/qa", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ contractId, question: q }),
      });
      if (!res.ok) throw new Error(await res.text());
      const { answer, references, source } = (await res.json()) as { answer: string; references?: string[]; source?: string };
      setMessages((prev) => [...prev, { role: "assistant", content: answer, references, source }]);
    } catch (err) {
      setError((err as Error).message || "답변을 가져오지 못했어요.");
    } finally {
      setLoading(false);
    }
  }

  function send(e: React.FormEvent) {
    e.preventDefault();
    void ask(input);
  }

  const isEmpty = messages.length === 0 && !loading;

  return (
    <div className="rounded-2xl bg-white border border-grey-200 overflow-hidden">
      <div ref={listRef} className="max-h-[420px] overflow-y-auto px-4 py-5">
        {isEmpty ? (
          <EmptyState onPick={(q) => setInput(q)} />
        ) : (
          <div className="flex flex-col gap-3">
            {messages.map((m, i) =>
              m.role === "user" ? (
                <UserBubble key={i} text={m.content} />
              ) : (
                <AssistantBubble key={i} text={m.content} references={m.references} source={m.source} />
              )
            )}
            {loading && <AssistantTyping />}
          </div>
        )}
      </div>

      {error && (
        <div className="mx-3 mt-3 rounded-xl bg-danger-bg px-3 py-2 text-[12px] font-medium text-danger">
          {error}
        </div>
      )}

      <form onSubmit={send} className="border-t border-grey-200 bg-grey-50 p-3 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="궁금한 점을 입력해주세요"
          disabled={loading}
          className="flex-1 h-11 rounded-full bg-white border border-grey-200 px-4 text-[14px] font-medium text-grey-900 placeholder-grey-400 focus:border-toss-blue focus:outline-none transition-colors disabled:bg-grey-100"
        />
        <button
          type="submit"
          disabled={loading || input.trim().length === 0}
          aria-label="질문 전송"
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-toss-blue text-white hover:bg-toss-blue-hover disabled:bg-grey-200 disabled:text-grey-400 transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center text-center py-6">
      <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-toss-blue-bg text-toss-blue">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8z" />
        </svg>
      </span>
      <p className="mt-3 text-[15px] font-bold text-grey-900">무엇이든 물어보세요</p>
      <p className="mt-1 text-[12px] text-grey-500">계약서·근로기준법에 대해 자유롭게 질문해주세요</p>
      <div className="mt-4 flex flex-wrap justify-center gap-1.5">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-full border border-grey-200 bg-white px-3 py-1.5 text-[12px] font-medium text-grey-700 hover:border-toss-blue hover:text-toss-blue transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-md bg-toss-blue px-4 py-3 text-[14px] leading-6 text-white whitespace-pre-wrap">
        {text}
      </div>
    </div>
  );
}

function AssistantBubble({ text, references, source }: { text: string; references?: string[]; source?: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-toss-blue-bg text-toss-blue">
        <span className="h-1.5 w-1.5 rounded-full bg-toss-blue" />
      </span>
      <div className="min-w-0 max-w-[82%]">
        <div className="rounded-2xl rounded-bl-md bg-grey-100 px-4 py-3 text-[14px] leading-6 text-grey-900 whitespace-pre-wrap">
          {text}
        </div>
        {(references?.length || source) && (
          <p className="mt-1 pl-1 text-[11px] text-grey-500">
            {references?.length ? `근거: ${references.join(", ")}` : ""}
            {source ? ` · ${source}` : ""}
          </p>
        )}
      </div>
    </div>
  );
}

function AssistantTyping() {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-toss-blue-bg text-toss-blue">
        <span className="h-1.5 w-1.5 rounded-full bg-toss-blue" />
      </span>
      <div className="rounded-2xl rounded-bl-md bg-grey-100 px-4 py-3">
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-grey-400 animate-bounce [animation-delay:-0.3s]" />
          <span className="h-1.5 w-1.5 rounded-full bg-grey-400 animate-bounce [animation-delay:-0.15s]" />
          <span className="h-1.5 w-1.5 rounded-full bg-grey-400 animate-bounce" />
        </span>
      </div>
    </div>
  );
}
