import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTravelStore } from '../store/useTravelStore';
import { useApiKeyStore } from '../store/useApiKeyStore';
import { ANALYSIS_FLOW } from '../mocks/analysisFlow';
import { streamRecommendation } from '../api/recommend';
import { Button, PageLayout } from '../components/common';
import { AgentStepCard, StepIndicator } from '../components/analyzing';
import type { AgentEvent, AgentId } from '../types';

const STEP_BY_AGENT: Record<AgentId, number> = {
  'input-validation': 0,
  'saju-analysis': 1,
  'travel-style-mapping': 2,
  'destination-retrieval': 3,
  'ranking': 4,
  'response-generation': 5,
};

export default function AnalyzingPage() {
  const navigate = useNavigate();
  const userInput = useTravelStore((s) => s.userInput);
  const setPipelineResult = useTravelStore((s) => s.setPipelineResult);
  const apiKey = useApiKeyStore((s) => s.apiKey);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startedRef = useRef(false);

  useEffect(() => {
    if (!userInput || apiKey.trim().length < 8) {
      navigate('/input', { replace: true });
      return;
    }
    if (startedRef.current) return;
    startedRef.current = true;

    const controller = new AbortController();

    const run = async () => {
      try {
        const result = await streamRecommendation(
          { apiKey, userInput },
          {
            signal: controller.signal,
            onEvent: (event: AgentEvent) => {
              if (event.type === 'agent_start' && event.agent) {
                setCurrentIndex(STEP_BY_AGENT[event.agent]);
              } else if (event.type === 'agent_done' && event.agent) {
                const idx = STEP_BY_AGENT[event.agent];
                setCurrentIndex(Math.min(idx + 1, ANALYSIS_FLOW.length - 1));
              }
            },
          },
        );
        setPipelineResult(result);
        setDone(true);
        setTimeout(() => {
          if (!controller.signal.aborted) {
            navigate('/result', { replace: true });
          }
        }, 400);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError((err as Error).message);
      }
    };
    run();

    return () => {
      controller.abort();
    };
  }, [userInput, apiKey, setPipelineResult, navigate]);

  if (!userInput) return null;

  return (
    <PageLayout background="mystic">
      <div className="relative flex-1 flex flex-col">
        <div
          className="absolute inset-0 pointer-events-none overflow-hidden"
          aria-hidden="true"
        >
          <span className="absolute top-[6%] left-[8%] text-xl opacity-50 animate-pulse">
            ✨
          </span>
          <span className="absolute top-[14%] right-[10%] text-base opacity-40 animate-pulse [animation-delay:0.6s]">
            ⭐
          </span>
          <span className="absolute bottom-[10%] left-[12%] text-lg opacity-40 animate-pulse [animation-delay:1.0s]">
            ✨
          </span>
        </div>

        <header className="relative pt-2 pb-6 text-center">
          <div className="text-5xl mb-3" aria-hidden="true">
            🔮
          </div>
          <h1 className="text-xl font-extrabold text-gradient-primary tracking-tight">
            당신의 사주를 풀어내고 있어요
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            잠시만 기다려 주세요. 하늘의 결을 천천히 살펴보는 중...
          </p>
        </header>

        <div className="relative mb-5">
          <StepIndicator
            total={ANALYSIS_FLOW.length}
            currentIndex={currentIndex}
            done={done}
          />
        </div>

        <div className="relative flex-1 flex flex-col gap-2.5 overflow-y-auto pb-4">
          {ANALYSIS_FLOW.map((step, idx) => {
            const state =
              done || idx < currentIndex
                ? 'done'
                : idx === currentIndex
                  ? 'active'
                  : 'pending';
            return (
              <AgentStepCard
                key={step.id}
                index={step.id}
                title={step.title}
                description={step.description}
                state={state}
              />
            );
          })}
        </div>

        {error && (
          <div className="relative mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <p className="font-semibold mb-1">분석 중 문제가 발생했어요</p>
            <p className="text-xs leading-relaxed">{error}</p>
            <div className="mt-3 flex gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate('/input', { replace: true })}
              >
                입력 화면으로
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  startedRef.current = false;
                  setError(null);
                  setCurrentIndex(0);
                  // Force re-run by toggling state. Simplest: reload the page.
                  window.location.reload();
                }}
              >
                다시 시도
              </Button>
            </div>
          </div>
        )}

        <footer className="relative pt-3 pb-1 text-center">
          <p className="text-[11px] text-gray-400">
            본 결과는 재미와 참고용입니다
          </p>
        </footer>
      </div>
    </PageLayout>
  );
}
