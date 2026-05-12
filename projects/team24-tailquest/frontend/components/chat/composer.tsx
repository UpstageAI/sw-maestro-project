"use client";

import { useEffect, useRef } from "react";

import { Icon } from "@/components/chrome/icon";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  /** Optional shortcut for "I don't know" responses — bypasses the textarea. */
  onDontKnow?: () => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
}

export function Composer({
  value,
  onChange,
  onSubmit,
  onDontKnow,
  disabled,
  loading,
  placeholder = "답변을 입력하고 Enter (Shift+Enter 줄바꿈)",
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize the textarea up to ~6 rows.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  }, [value]);

  const charCount = value.length;
  const canSubmit = !disabled && !loading && value.trim().length > 0;

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSubmit) onSubmit();
    }
  }

  return (
    <div className="bg-canvas border border-hairline focus-within:border-ink rounded-md p-md transition-colors">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || loading}
        rows={2}
        placeholder={placeholder}
        className="block w-full bg-transparent text-body-md text-ink placeholder:text-muted-soft outline-none focus:outline-none focus-visible:outline-none resize-none min-h-[64px]"
        style={{ boxShadow: "none" }}
      />
      <div className="flex items-center justify-between gap-md pt-sm border-t border-hairline-soft mt-sm">
        <span className="text-caption-sm text-muted">
          {charCount.toLocaleString()}자
        </span>
        <div className="flex items-center gap-sm">
          {onDontKnow && (
            <button
              type="button"
              onClick={onDontKnow}
              disabled={disabled || loading}
              className="inline-flex items-center gap-xs px-md py-xs rounded-md text-button-sm border border-hairline text-ink bg-canvas hover:bg-paper transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Icon name="help" size={16} />
              잘 모르겠어요
            </button>
          )}
          <button
            type="button"
            onClick={onSubmit}
            disabled={!canSubmit}
            className="btn-primary"
          >
            {loading ? (
              <>
                <Icon name="hourglass_top" size={18} />
                분석 중
              </>
            ) : (
              <>
                답변 제출
                <Icon name="arrow_forward" size={18} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
