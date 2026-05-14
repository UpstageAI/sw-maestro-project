interface Props {
  step: 1 | 2 | 3;
}

const steps = ['입력', '수집', '브리핑'];

export default function StepIndicator({ step }: Props) {
  return (
    <div className="flex items-center gap-1 mb-6">
      {steps.map((label, i) => {
        const num = i + 1;
        const active = num === step;
        const done = num < step;
        return (
          <div key={num} className="flex items-center gap-1">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all
              ${done
                ? 'bg-indigo-50 text-indigo-500'
                : active
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200'
                  : 'bg-slate-100 text-slate-400'}`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold
                ${done ? 'bg-indigo-500 text-white' : active ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-500'}`}>
                {done ? '✓' : num}
              </span>
              <span>{label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`h-px w-4 mx-1 transition-colors ${done ? 'bg-indigo-300' : 'bg-slate-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
