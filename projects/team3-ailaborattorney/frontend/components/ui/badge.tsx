import * as React from "react";
type Tone = "neutral" | "blue" | "success" | "warning" | "danger";
const tones: Record<Tone, string> = {
  neutral: "bg-grey-100 text-grey-700",
  blue: "bg-toss-blue-bg text-toss-blue",
  success: "bg-success-bg text-success",
  warning: "bg-warning-bg text-warning",
  danger: "bg-danger-bg text-danger",
};
export function Badge({ tone = "neutral", className = "", children }: { tone?: Tone; className?: string; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[12px] font-semibold ${tones[tone]} ${className}`}>
      {children}
    </span>
  );
}
