type Risk = "low" | "medium" | "high";

const tone: Record<Risk, string> = {
  low: "bg-success-bg text-success",
  medium: "bg-warning-bg text-warning",
  high: "bg-danger-bg text-danger",
};

const labels: Record<Risk, string> = {
  low: "안전",
  medium: "주의",
  high: "위반 가능",
};

export default function RiskBadge({ level }: { level: Risk }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold tracking-tight ${tone[level]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {labels[level]}
    </span>
  );
}
