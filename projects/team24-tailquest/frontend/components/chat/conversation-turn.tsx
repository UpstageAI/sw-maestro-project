"use client";

import { useState } from "react";
import { Icon } from "@/components/chrome/icon";
import { InlineAnalysis } from "@/components/chat/inline-analysis";
import { MessageBubble } from "@/components/chat/message-bubble";
import { PraiseBubble } from "@/components/chat/praise-bubble";
import type { Turn } from "@/lib/chat-state";
import type { Citation } from "@/lib/api";

/** Score threshold (0-100) above which an answer is considered "excellent"
 *  and warrants a praise bubble in addition to (or instead of) critique notes. */
const EXCELLENT_SCORE = 85;

interface ConversationTurnProps {
  turn: Turn;
}

export function ConversationTurn({ turn }: ConversationTurnProps) {
  // Praise only when the analyzer didn't flag anything critical or moderate.
  // Without this, a high-score answer could simultaneously get "잘했어요" plus
  // an InlineAnalysis card listing serious gaps — which reads as contradictory.
  const hasSeriousIssue = (turn.notes ?? []).some(
    (n) => n.severity === "critical" || n.severity === "moderate",
  );
  const showPraise =
    turn.answerQuality === "good" &&
    typeof turn.score === "number" &&
    turn.score >= EXCELLENT_SCORE &&
    !hasSeriousIssue;

  return (
    <div className="flex flex-col gap-md">
      <MessageBubble who="interviewer">
        <p className="text-body-md text-ink leading-relaxed">{turn.question}</p>
      </MessageBubble>

      {turn.citations && turn.citations.length > 0 && (
        <CitationsCard citations={turn.citations} />
      )}

      {turn.answer && (
        <MessageBubble who="user">
          <p className="text-body-md leading-relaxed whitespace-pre-wrap">
            {turn.answer}
          </p>
        </MessageBubble>
      )}

      {turn.explanation && (
        <ExplanationBubble text={turn.explanation} quality={turn.answerQuality} />
      )}

      {showPraise && <PraiseBubble />}

      {turn.notes && turn.notes.length > 0 && turn.answerQuality === "good" && (
        <InlineAnalysis notes={turn.notes} />
      )}
    </div>
  );
}

// ---------- Sub-components ----------

interface CitationsCardProps {
  citations: Citation[];
}

export function CitationsCard({ citations }: CitationsCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="ml-14 max-w-[80%]">
      <div className="rounded-md border border-hairline bg-surface-soft overflow-hidden">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="w-full flex items-center justify-between px-md py-sm text-left"
        >
          <span className="flex items-center gap-sm text-caption-sm text-muted">
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
              menu_book
            </span>
            참고 자료 {citations.length}건
          </span>
          <Icon
            name={open ? "expand_less" : "expand_more"}
            size={16}
            className="text-muted"
          />
        </button>

        {open && (
          <ul className="border-t border-hairline flex flex-col divide-y divide-hairline">
            {citations.map((c, i) => (
              <li key={i} className="px-md py-sm">
                <p className="text-caption-sm text-muted mb-xxs">
                  {c.url ? (
                    <a href={c.url} target="_blank" rel="noreferrer" className="hover:underline text-legal-link">
                      {c.file_name}{c.heading ? `#${c.heading}` : ""}
                    </a>
                  ) : (
                    <>{c.file_name}{c.heading ? `#${c.heading}` : ""}</>
                  )}
                </p>
                <p className="text-body-sm text-ink italic border-l-2 border-hairline pl-md leading-relaxed line-clamp-5">
                  {c.excerpt}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function ExplanationBubble({
  text,
  quality,
}: {
  text: string;
  quality?: "good" | "uncertain" | "incorrect";
}) {
  const label =
    quality === "incorrect"
      ? "잠깐, 짚고 넘어갈게요"
      : "괜찮아요. 짧게 알려드릴게요";

  return (
    <div className="flex gap-md">
      <div className="shrink-0">
        <span className="h-10 w-10 rounded-full bg-ink text-on-dark flex items-center justify-center">
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
            menu_book
          </span>
        </span>
      </div>
      <div className="flex-1 min-w-0 max-w-[80%]">
        <div className="flex items-center gap-sm mb-sm">
          <span className="text-caption-sm text-muted">TailQuest 면접관</span>
          <span className="pill bg-ink text-on-dark">{label}</span>
        </div>
        <div className="rounded-md border-l-4 border-ink bg-canvas p-md shadow-airbnb">
          <p className="text-body-md text-ink leading-relaxed whitespace-pre-wrap">
            {text}
          </p>
        </div>
      </div>
    </div>
  );
}
