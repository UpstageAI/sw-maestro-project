import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTravelStore } from '../store/useTravelStore';
import { useApiKeyStore } from '../store/useApiKeyStore';
import { TRAVEL_STYLES, type StyleKey } from '../mocks/travelStyles';
import { findEnrichedDestinationById } from '../utils/destinationLookup';
import { Button, Card, PageLayout } from '../components/common';
import {
  DestinationCard,
  DisclaimerBox,
  SajuSummary,
  StyleBadge,
} from '../components/result';
import type { RankedDestinationDto } from '../types';

type SortMode = 'match' | 'distance';

export default function ResultPage() {
  const navigate = useNavigate();
  const pipelineResult = useTravelStore((s) => s.pipelineResult);
  const userInput = useTravelStore((s) => s.userInput);
  const reset = useTravelStore((s) => s.reset);
  const resetResultOnly = useTravelStore((s) => s.resetResultOnly);
  const clearApiKey = useApiKeyStore((s) => s.clearApiKey);

  const [sortMode, setSortMode] = useState<SortMode>('match');

  useEffect(() => {
    if (!pipelineResult || !userInput) {
      navigate('/input', { replace: true });
    }
  }, [pipelineResult, userInput, navigate]);

  const sortedRanked = useMemo(() => {
    if (!pipelineResult || !userInput) return [];
    const list = pipelineResult.ranked.slice();
    if (sortMode === 'distance') {
      list.sort(
        (a, b) =>
          a.destination.travelTime[userInput.departure] -
          b.destination.travelTime[userInput.departure],
      );
    } else {
      list.sort((a, b) => b.score.total - a.score.total);
    }
    return list;
  }, [pipelineResult, userInput, sortMode]);

  if (!pipelineResult || !userInput) return null;

  const styles: StyleKey[] = pipelineResult.selectedStyles.filter(
    (s): s is StyleKey => s in TRAVEL_STYLES,
  );

  return (
    <PageLayout background="cream">
      <header className="pt-2 pb-5">
        <div className="flex items-center gap-1.5 text-xs text-primary mb-2">
          <span aria-hidden="true">✨</span>
          <span className="font-semibold tracking-wide">분석 완료</span>
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900 leading-tight">
          {pipelineResult.headline}
        </h1>
      </header>

      <div className="flex-1 flex flex-col gap-5 overflow-y-auto pb-8">
        <SajuSummary saju={pipelineResult.saju} />

        <Card padding="lg" className="bg-white">
          <div className="flex flex-wrap gap-2 mb-3">
            {styles.map((k) => (
              <StyleBadge key={k} style={TRAVEL_STYLES[k]} />
            ))}
          </div>
          <p className="text-sm leading-relaxed text-gray-700">
            {pipelineResult.styleReason}
          </p>
        </Card>

        <section>
          <div className="flex items-baseline justify-between mb-3 px-1">
            <h2 className="text-base font-extrabold text-gray-900 tracking-tight">
              추천 여행지 <span className="text-gradient-primary">Top 3</span>
            </h2>
            <div className="inline-flex rounded-full bg-cream-dark p-0.5 text-[11px] font-semibold">
              <SortToggleButton
                active={sortMode === 'match'}
                onClick={() => setSortMode('match')}
              >
                결 맞춤순
              </SortToggleButton>
              <SortToggleButton
                active={sortMode === 'distance'}
                onClick={() => setSortMode('distance')}
              >
                가까운순
              </SortToggleButton>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            {sortedRanked.map((r, idx) => (
              <RankedCard
                key={r.destination.id}
                rank={idx + 1}
                ranked={r}
                travelTimeHours={
                  r.destination.travelTime[userInput.departure]
                }
              />
            ))}
          </div>
        </section>

        <DisclaimerBox />
      </div>

      <div className="pt-3 pb-1 flex flex-col gap-2">
        <Button
          variant="primary"
          size="lg"
          fullWidth
          onClick={() => {
            // Keep the user input + API key, drop only the analysis result.
            resetResultOnly();
            navigate('/input');
          }}
        >
          조건 바꿔서 다시 받기
        </Button>
        <Button
          variant="ghost"
          size="md"
          fullWidth
          onClick={() => {
            // Full reset: clear input, result, AND the API key.
            reset();
            clearApiKey();
            navigate('/');
          }}
        >
          처음으로
        </Button>
      </div>
    </PageLayout>
  );
}

function SortToggleButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={[
        'rounded-full px-3 py-1 transition-colors',
        active
          ? 'bg-white text-primary shadow-soft'
          : 'text-gray-500 hover:text-gray-700',
      ].join(' ')}
    >
      {children}
    </button>
  );
}

function RankedCard({
  rank,
  ranked,
  travelTimeHours,
}: {
  rank: number;
  ranked: RankedDestinationDto;
  travelTimeHours: number;
}) {
  const enriched = findEnrichedDestinationById(ranked.destination.id);
  if (!enriched) return null;
  return (
    <DestinationCard
      rank={rank}
      destination={enriched}
      reason={ranked.reason}
      score={ranked.score}
      travelTimeHours={travelTimeHours}
    />
  );
}
