import type { EnrichedDestination } from '../../mocks/destinations';
import type { ScoreBreakdown } from '../../types';
import ReasonBlock from './ReasonBlock';

interface DestinationCardProps {
  rank: number;
  destination: EnrichedDestination;
  reason: string;
  score?: ScoreBreakdown;
  travelTimeHours?: number;
}

export default function DestinationCard({
  rank,
  destination,
  reason,
  score,
  travelTimeHours,
}: DestinationCardProps) {
  return (
    <article className="bg-white rounded-2xl shadow-card overflow-hidden border border-cream-dark">
      <div className="relative bg-mystic px-5 pt-5 pb-4">
        <div className="absolute top-3 left-3 inline-flex items-center justify-center w-8 h-8 rounded-full bg-primary text-white text-sm font-bold shadow-soft">
          {rank}
        </div>

        {typeof travelTimeHours === 'number' && (
          <div className="absolute top-3 right-3 inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-0.5 text-[11px] font-semibold text-primary">
            ⏱ {formatHours(travelTimeHours)}
          </div>
        )}

        <div className="flex items-center justify-center text-6xl mb-2 select-none" aria-hidden="true">
          {destination.emoji}
        </div>

        <div className="text-center">
          <p className="text-xs font-medium text-primary/80">
            {destination.region}
          </p>
          <h3 className="mt-0.5 text-xl font-extrabold text-gray-900 tracking-tight">
            {destination.name}
          </h3>
        </div>
      </div>

      <div className="px-5 py-4 space-y-3.5">
        <p className="text-sm text-gray-700 leading-relaxed">
          {destination.description}
        </p>

        {score && <ScoreBars score={score} />}

        <div className="flex flex-wrap gap-1.5">
          {destination.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full bg-cream-dark text-primary"
            >
              #{tag}
            </span>
          ))}
        </div>

        <div>
          <h4 className="text-xs font-bold text-gray-500 mb-1.5 tracking-wide">
            추천 활동
          </h4>
          <ul className="space-y-1">
            {destination.activities.slice(0, 3).map((activity) => (
              <li
                key={activity}
                className="flex items-start gap-2 text-sm text-gray-700"
              >
                <span className="mt-1 inline-block w-1 h-1 rounded-full bg-gold shrink-0" aria-hidden="true" />
                <span>{activity}</span>
              </li>
            ))}
          </ul>
        </div>

        <ReasonBlock>{reason}</ReasonBlock>
      </div>
    </article>
  );
}

function ScoreBars({ score }: { score: ScoreBreakdown }) {
  const rows: Array<{ label: string; value: number; color: string }> = [
    { label: '사주 적합도', value: score.saju, color: 'bg-primary' },
    { label: '선호 매칭', value: score.preference, color: 'bg-pink-400' },
    { label: '거리', value: score.distance, color: 'bg-emerald-400' },
  ];
  return (
    <div className="rounded-xl bg-cream-dark/40 px-3 py-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[11px] font-bold text-gray-500 tracking-wide">
          매칭 점수
        </span>
        <span className="text-xs font-bold text-primary">
          종합 {score.total.toFixed(1)}
        </span>
      </div>
      <div className="space-y-1">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center gap-2">
            <span className="w-16 text-[11px] text-gray-600">{r.label}</span>
            <div className="flex-1 h-1.5 rounded-full bg-white overflow-hidden">
              <div
                className={`h-full ${r.color}`}
                style={{ width: `${Math.max(0, Math.min(100, r.value))}%` }}
              />
            </div>
            <span className="w-7 text-right text-[11px] font-medium text-gray-600">
              {Math.round(r.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatHours(h: number): string {
  if (h < 1) return `${Math.round(h * 60)}분`;
  return `${h.toFixed(h % 1 === 0 ? 0 : 1)}시간`;
}
