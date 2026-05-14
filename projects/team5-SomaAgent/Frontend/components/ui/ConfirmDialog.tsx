"use client";

import { Loader2, X } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import type { ReactNode } from "react";

type Tone = "primary" | "danger";

type Props = {
  open: boolean;
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: Tone;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

const CONFIRM_BUTTON: Record<Tone, string> = {
  primary:
    "bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white",
  danger:
    "bg-rose-600 hover:bg-rose-700 disabled:bg-rose-400 text-white",
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "확인",
  cancelLabel = "취소",
  tone = "primary",
  busy = false,
  onConfirm,
  onCancel,
}: Props) {
  const titleId = useId();
  const descId = useId();
  const confirmRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) {
        event.preventDefault();
        onCancel();
      }
    };
    document.addEventListener("keydown", onKey);
    confirmRef.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descId}
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      <button
        type="button"
        aria-label="모달 닫기"
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
        onClick={() => !busy && onCancel()}
        tabIndex={-1}
      />

      <div className="relative w-full max-w-sm overflow-hidden rounded-2xl bg-white shadow-xl">
        <header className="flex items-start justify-between gap-3 px-5 pt-5">
          <h3
            id={titleId}
            className="text-base font-semibold tracking-tight text-slate-900"
          >
            {title}
          </h3>
          <button
            type="button"
            aria-label="닫기"
            onClick={onCancel}
            disabled={busy}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div
          id={descId}
          className="px-5 pb-5 pt-2 text-sm leading-relaxed text-slate-600"
        >
          {description}
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-slate-100 bg-slate-50/70 px-5 py-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={`inline-flex min-w-[88px] items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${CONFIRM_BUTTON[tone]} disabled:cursor-not-allowed`}
          >
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}
            {confirmLabel}
          </button>
        </footer>
      </div>
    </div>
  );
}
