"use client";

import type { FeedbackAction } from "@/lib/api";

interface FeedbackBarProps {
  onAction: (action: FeedbackAction) => void;
  loading: boolean;
  /** When true (e.g. feedback limit reached) only the accept button is active. */
  disabled?: boolean;
  /** Hint shown when disabled is true. */
  disabledHint?: string;
}

interface ActionButton {
  action: FeedbackAction;
  label: string;
  icon: string;
  isPrimary?: boolean;
}

const BUTTONS: ActionButton[] = [
  { action: "regenerate", label: "다시 만들어줘", icon: "replay" },
  { action: "refine_harder", label: "더 어렵게", icon: "trending_up" },
  { action: "refine_easier", label: "더 쉽게", icon: "trending_down" },
  { action: "accept", label: "좋아요, 다음 질문", icon: "check", isPrimary: true },
];

export function FeedbackBar({
  onAction,
  loading,
  disabled = false,
  disabledHint,
}: FeedbackBarProps) {
  return (
    <div className="flex flex-col gap-xs">
      {disabled && disabledHint && (
        <p className="text-caption-sm text-graphite px-xs">{disabledHint}</p>
      )}
      <div className="flex flex-wrap items-center gap-xs px-xs">
        <span className="text-caption-sm text-graphite mr-xs">이 질문 어떠셨어요?</span>

        {BUTTONS.map(({ action, label, icon, isPrimary }) => {
          const isAccept = action === "accept";
          // When disabled, only accept is enabled
          const isDisabled = loading || (disabled && !isAccept);

          return (
            <button
              key={action}
              type="button"
              aria-label={label}
              disabled={isDisabled}
              onClick={() => onAction(action)}
              className={[
                "inline-flex items-center gap-xs px-sm py-xs rounded-md text-caption-sm transition-colors",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                isPrimary
                  ? "bg-rausch text-white hover:opacity-90 font-medium"
                  : "border border-hairline text-ink bg-canvas hover:bg-paper",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 14, lineHeight: 1 }}
                aria-hidden="true"
              >
                {icon}
              </span>
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
