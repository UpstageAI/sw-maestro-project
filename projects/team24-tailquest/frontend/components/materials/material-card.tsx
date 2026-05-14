"use client";

import { Icon } from "@/components/chrome/icon";
import { cn } from "@/lib/utils";
import type { MaterialResponse } from "@/lib/api";

const KIND_ICON: Record<MaterialResponse["kind"], string> = {
  md: "markdown",
  pdf: "picture_as_pdf",
  github: "code",
};

const KIND_LABEL: Record<MaterialResponse["kind"], string> = {
  md: "MD",
  pdf: "PDF",
  github: "GitHub",
};

const STATUS_STYLE: Record<MaterialResponse["status"], string> = {
  ready: "bg-emerald-50 text-emerald-700",
  indexing: "bg-amber-50 text-amber-700",
  failed: "bg-rose-50 text-rose-700",
};

const STATUS_LABEL: Record<MaterialResponse["status"], string> = {
  ready: "완료",
  indexing: "인덱싱 중",
  failed: "실패",
};

interface Props {
  item: MaterialResponse;
  selected: boolean;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
}

export function MaterialCard({ item, selected, onToggle, onDelete }: Props) {
  // Only ready materials are selectable — indexing/failed entries shouldn't be
  // attached to a session because Chroma either has no chunks yet or never
  // will. We dim the row visually and use cursor-not-allowed on the label so
  // the affordance matches the disabled checkbox.
  const selectable = item.status === "ready";
  return (
    <li
      className={cn(
        "flex items-start gap-md rounded-md border bg-canvas p-md transition-colors",
        selected ? "border-ink" : "border-hairline hover:border-border-strong",
        !selectable && "opacity-70",
      )}
    >
      {/* Checkbox */}
      <label
        className={cn(
          "shrink-0 flex items-center mt-xxs",
          selectable ? "cursor-pointer" : "cursor-not-allowed",
        )}
        title={selectable ? undefined : "인덱싱이 끝나야 선택할 수 있어요."}
      >
        <input
          type="checkbox"
          checked={selected}
          onChange={() => selectable && onToggle(item.id)}
          disabled={!selectable}
          className="h-4 w-4 accent-ink rounded-sm disabled:cursor-not-allowed"
          aria-label={`${item.name} 선택`}
        />
      </label>

      {/* Icon */}
      <span className="h-9 w-9 rounded-sm bg-surface-strong text-ink flex items-center justify-center shrink-0">
        <Icon name={KIND_ICON[item.kind]} size={18} />
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-sm flex-wrap mb-xxs">
          {/* Kind badge */}
          <span className="pill bg-surface-strong text-ink">
            {KIND_LABEL[item.kind]}
          </span>
          {/* Status pill */}
          <span className={cn("pill", STATUS_STYLE[item.status])}>
            {item.status === "indexing" && (
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
            )}
            {STATUS_LABEL[item.status]}
          </span>
        </div>

        <p className="text-body-sm text-ink truncate font-medium">{item.name}</p>

        <div className="flex items-center gap-sm mt-xxs">
          {item.status === "ready" && (
            <span className="text-caption-sm text-muted">
              {item.chunks}개 청크
            </span>
          )}
          {item.status === "failed" && item.error && (
            <span className="text-caption-sm text-error-text truncate">
              {item.error}
            </span>
          )}
        </div>
      </div>

      {/* Delete */}
      <button
        type="button"
        onClick={() => onDelete(item.id)}
        aria-label={`${item.name} 삭제`}
        className="shrink-0 p-1 text-muted hover:text-ink transition-colors"
      >
        <Icon name="delete" size={18} />
      </button>
    </li>
  );
}
