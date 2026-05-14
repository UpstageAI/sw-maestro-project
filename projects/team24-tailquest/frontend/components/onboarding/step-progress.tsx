import { cn } from "@/lib/utils";

interface Props {
  steps: { id: number; label: string }[];
  current: number;
}

export function StepProgress({ steps, current }: Props) {
  return (
    <ol className="flex items-center gap-md max-w-3xl mx-auto" aria-label="진행 단계">
      {steps.map((s, i) => {
        const active = s.id === current;
        const done = s.id < current;
        return (
          <li key={s.id} className="flex items-center gap-md flex-1 last:flex-initial">
            <div className="flex items-center gap-md">
              <span
                className={cn(
                  "h-8 w-8 rounded-full flex items-center justify-center tabular-nums text-button-sm transition-colors",
                  active && "bg-ink text-on-dark",
                  done && "bg-rausch text-on-primary",
                  !active && !done && "bg-surface-strong text-muted",
                )}
              >
                {done ? "✓" : s.id}
              </span>
              <span
                className={cn(
                  "text-button-sm whitespace-nowrap",
                  active ? "text-ink" : "text-muted",
                )}
              >
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <span
                className={cn(
                  "h-px flex-1 transition-colors",
                  done ? "bg-rausch" : "bg-hairline",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
