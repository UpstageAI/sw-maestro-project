"use client";

import { Icon } from "@/components/chrome/icon";
import { cn } from "@/lib/utils";
import type { Domain } from "@/lib/domains";

interface Props {
  domains: Domain[];
  selected: string[];
  onToggle: (id: string) => void;
}

/** Compact domain grid — paddings/typography reduced so 6+ cards fit
 *  in a single viewport without scrolling. Seed-question preview kept
 *  but truncated to 1 line. */
export function DomainGrid({ domains, selected, onToggle }: Props) {
  return (
    <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-sm">
      {domains.map((d) => {
        const isSelected = selected.includes(d.id);
        return (
          <li key={d.id}>
            <button
              type="button"
              onClick={() => onToggle(d.id)}
              aria-pressed={isSelected}
              className={cn(
                "group w-full text-left rounded-md border bg-canvas p-md transition-all relative h-full",
                isSelected
                  ? "border-ink border-2 bg-surface-soft"
                  : "border-hairline hover:border-ink hover:shadow-airbnb",
              )}
            >
              <div className="flex items-start justify-between mb-sm">
                <span
                  className={cn(
                    "h-9 w-9 rounded-md flex items-center justify-center transition-colors shrink-0",
                    isSelected
                      ? "bg-rausch text-on-primary"
                      : "bg-surface-strong text-ink group-hover:bg-ink group-hover:text-on-dark",
                  )}
                >
                  <Icon name={d.icon} size={20} filled />
                </span>
                <span
                  className={cn(
                    "h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors",
                    isSelected
                      ? "bg-ink border-ink text-on-dark"
                      : "border-hairline group-hover:border-ink",
                  )}
                  aria-hidden
                >
                  {isSelected && <Icon name="check" size={12} />}
                </span>
              </div>
              <h3 className="text-title-md text-ink mb-1">{d.label}</h3>
              <p className="text-caption-sm text-muted truncate">
                {d.topics.slice(0, 4).join(" · ")}
              </p>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
