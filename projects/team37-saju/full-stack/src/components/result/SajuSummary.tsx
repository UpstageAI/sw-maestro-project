import type { Element, SajuAnalysis } from '../../types';

interface SajuSummaryProps {
  saju: SajuAnalysis;
}

const ELEMENT_ORDER: Element[] = ['목', '화', '토', '금', '수'];

const ELEMENT_COLORS: Record<Element, { fill: string; chip: string; text: string }> = {
  목: { fill: 'bg-emerald-400', chip: 'bg-emerald-50', text: 'text-emerald-700' },
  화: { fill: 'bg-rose-400', chip: 'bg-rose-50', text: 'text-rose-700' },
  토: { fill: 'bg-amber-400', chip: 'bg-amber-50', text: 'text-amber-700' },
  금: { fill: 'bg-slate-400', chip: 'bg-slate-100', text: 'text-slate-700' },
  수: { fill: 'bg-sky-400', chip: 'bg-sky-50', text: 'text-sky-700' },
};

export default function SajuSummary({ saju }: SajuSummaryProps) {
  const max = Math.max(...ELEMENT_ORDER.map((e) => saju.elements.scores[e]));

  return (
    <section className="rounded-2xl bg-white border border-cream-dark px-5 py-4 shadow-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-extrabold text-gray-900 tracking-tight">
          🔮 내 사주의 결
        </h3>
        <span className="text-[11px] font-medium text-gray-500">
          일간 {saju.chart.dayMaster.stem} ({saju.chart.dayMaster.element})
        </span>
      </div>

      <div className="space-y-1.5 mb-3">
        {ELEMENT_ORDER.map((el) => {
          const v = saju.elements.scores[el];
          const ratio = max > 0 ? (v / max) * 100 : 0;
          const isStrong = saju.elements.strong.includes(el);
          const isWeak = saju.elements.weak.includes(el);
          const isBoost = saju.needsBoost === el;
          return (
            <div key={el} className="flex items-center gap-2">
              <span
                className={[
                  'w-6 text-center text-xs font-bold',
                  isStrong
                    ? 'text-rose-600'
                    : isWeak
                      ? 'text-sky-600'
                      : 'text-gray-700',
                ].join(' ')}
              >
                {el}
              </span>
              <div className="flex-1 h-2 rounded-full bg-cream-dark/60 overflow-hidden">
                <div
                  className={`h-full ${ELEMENT_COLORS[el].fill}`}
                  style={{ width: `${ratio}%` }}
                />
              </div>
              <span className="w-9 text-right text-[11px] tabular-nums text-gray-500">
                {v.toFixed(1)}
              </span>
              {isBoost && (
                <span className="ml-1 inline-flex items-center rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                  보완
                </span>
              )}
            </div>
          );
        })}
      </div>

      {saju.personalityKeywords.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {saju.personalityKeywords.map((kw) => (
            <span
              key={kw}
              className="inline-flex items-center rounded-full bg-cream-dark px-2 py-0.5 text-[11px] font-medium text-primary"
            >
              {kw}
            </span>
          ))}
        </div>
      )}

      {saju.narrative && (
        <p className="text-sm leading-relaxed text-gray-700 mb-2">
          {saju.narrative}
        </p>
      )}
      {saju.yearlyEnergy && (
        <p className="text-xs leading-relaxed text-gray-500">
          {saju.yearlyEnergy}
        </p>
      )}
    </section>
  );
}
