"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface StepDef {
  key: string;
  label: string;
  short: string;
}

interface StepProgressProps {
  steps: StepDef[];
  current: number;
}

export function StepProgress({ steps, current }: StepProgressProps) {
  return (
    <div className="border-b border-border/60 bg-background/85 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 px-5 py-4">
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span>
            <span className="text-brand-blue">STEP {current + 1}</span> · {steps.length}단계
          </span>
          <span className="hidden sm:block">{steps[current]?.label}</span>
        </div>
        <ol className="flex items-center gap-2">
          {steps.map((step, i) => {
            const done = i < current;
            const active = i === current;
            return (
              <li key={step.key} className="flex flex-1 items-center gap-2">
                <div
                  className={cn(
                    "flex h-1.5 w-full overflow-hidden rounded-full",
                    done || active ? "bg-brand-blue/20" : "bg-muted",
                  )}
                >
                  <span
                    className={cn(
                      "h-full rounded-full transition-all duration-500 ease-out",
                      done || active ? "w-full bg-brand-blue" : "w-0",
                    )}
                  />
                </div>
                <div
                  className={cn(
                    "grid size-6 shrink-0 place-items-center rounded-full text-[10px] font-semibold",
                    done
                      ? "bg-brand-blue text-white"
                      : active
                        ? "border-2 border-brand-blue bg-background text-brand-blue"
                        : "border border-border bg-background text-muted-foreground",
                  )}
                >
                  {done ? <Check className="size-3" /> : i + 1}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
