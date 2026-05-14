"use client";

interface PraiseBubbleProps {
  /** Optional one-line headline pulled from the analyzer. */
  headline?: string;
}

/** Positive-tone bubble shown when the user's answer was solid enough that
 *  the analyzer didn't surface critical/moderate weaknesses. Sits between
 *  the user's answer and the InlineAnalysis card; co-existence is OK only
 *  when the remaining notes are all minor polish items. */
export function PraiseBubble({ headline }: PraiseBubbleProps) {
  return (
    <div className="flex gap-md">
      <div className="shrink-0">
        <span className="h-10 w-10 rounded-full bg-ink text-on-dark flex items-center justify-center">
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
            verified
          </span>
        </span>
      </div>
      <div className="flex-1 min-w-0 max-w-[80%]">
        <div className="flex items-center gap-sm mb-sm">
          <span className="text-caption-sm text-muted">TailQuest 면접관</span>
          <span className="pill bg-ink text-on-dark">잘했어요</span>
        </div>
        <div className="rounded-md border-l-4 border-ink bg-canvas p-md shadow-airbnb">
          <p className="text-body-md text-ink leading-relaxed">
            {headline ??
              "질문 의도에 맞춰 핵심을 잘 짚으셨습니다. 정의·동작·트레이드오프가 균형 있게 들어간 단단한 답변이에요."}
          </p>
        </div>
      </div>
    </div>
  );
}
