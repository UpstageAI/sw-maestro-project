interface StepIndicatorProps {
  total: number;
  currentIndex: number;
  done: boolean;
}

export default function StepIndicator({
  total,
  currentIndex,
  done,
}: StepIndicatorProps) {
  const completed = done ? total : currentIndex;
  const percent = Math.round((completed / total) * 100);

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-primary tracking-wide">
          AI 분석 중
        </span>
        <span className="text-xs text-gray-500 tabular-nums">
          {completed} / {total} ({percent}%)
        </span>
      </div>

      <div className="relative h-1.5 w-full bg-cream-dark rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary to-gold rounded-full transition-[width] duration-500 ease-out"
          style={{ width: `${percent}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
