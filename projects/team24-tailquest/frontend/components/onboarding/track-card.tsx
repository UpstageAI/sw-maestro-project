"use client";

import { Icon } from "@/components/chrome/icon";
import { cn } from "@/lib/utils";
import type { Track } from "@/lib/domains";

interface Props {
  trackId: Track;
  label: string;
  description: string;
  icon: string;
  examples: string[];
  selected: boolean;
  onSelect: () => void;
}

/** Compact horizontal track card — was vertical with a 5:3 photo plate.
 *  The photo plate ate too much height, pushing the bottom action bar off
 *  the viewport. This horizontal layout keeps the whole step on screen. */
export function TrackCard({
  label,
  description,
  icon,
  examples,
  selected,
  onSelect,
}: Props) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "group text-left rounded-md border bg-canvas p-lg transition-all flex items-start gap-lg w-full",
        selected
          ? "border-ink border-2 shadow-airbnb"
          : "border-hairline hover:border-ink hover:shadow-airbnb",
      )}
    >
      {/* Icon block — left-aligned, fixed size */}
      <span
        className={cn(
          "h-16 w-16 rounded-md flex items-center justify-center shrink-0 transition-colors",
          selected
            ? "bg-rausch text-on-primary"
            : "bg-surface-strong text-ink group-hover:bg-ink group-hover:text-on-dark",
        )}
      >
        <Icon name={icon} size={32} filled />
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-sm mb-1">
          <h3 className="text-display-sm text-ink">{label}</h3>
          {selected && (
            <span className="pill bg-ink text-on-dark">
              <Icon name="check" size={12} />
              선택됨
            </span>
          )}
        </div>
        <p className="text-body-sm text-muted mb-sm line-clamp-2">{description}</p>
        <ul className="flex flex-wrap gap-1">
          {examples.map((e) => (
            <li
              key={e}
              className="pill bg-surface-strong text-ink"
            >
              {e}
            </li>
          ))}
        </ul>
      </div>
    </button>
  );
}
