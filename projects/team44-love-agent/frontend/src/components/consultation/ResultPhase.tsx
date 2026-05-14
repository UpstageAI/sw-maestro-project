'use client';

import { useEffect, useRef } from 'react';
import { Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import type { Agent, FinalResult as FinalResultType } from '@/types';
import { SectionTitle } from '@/components/common';
import { Button } from '@/components/ui/button';
import { FinalResult } from './FinalResult';
import { FinalAgentSummary } from './FinalAgentSummary';
import { resultContent } from '@/content';

interface ResultPhaseProps {
  agents: Agent[];
  result: FinalResultType;
  onSave?: () => void;
  onShowFinalAdvice?: () => void;
  isLoadingFinalAdvice?: boolean;
}

export function ResultPhase({
  agents,
  result,
  onSave,
  onShowFinalAdvice,
  isLoadingFinalAdvice,
}: ResultPhaseProps) {
  const topRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // 페이지 진입 시 부모 스크롤 컨테이너를 맨 위로.
    topRef.current?.scrollIntoView({ behavior: 'auto', block: 'start' });
  }, []);

  return (
    <div ref={topRef} className="flex flex-col gap-6">
      <SectionTitle title={resultContent.title || '최종 결과'} />
      <FinalResult result={result} />

      {/* 🎯 큼지막한 "최종 조언" 버튼 — 결과 카드 아래, 에이전트 요약 위 */}
      {onShowFinalAdvice && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <Button
            onClick={onShowFinalAdvice}
            disabled={isLoadingFinalAdvice}
            className="relative h-20 w-full overflow-hidden text-xl font-bold"
            style={{
              backgroundImage:
                'linear-gradient(135deg, oklch(0.65 0.22 320) 0%, oklch(0.62 0.22 15) 50%, oklch(0.68 0.2 60) 100%)',
            }}
          >
            <motion.span
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ duration: 1.8, repeat: Infinity }}
              className="flex items-center gap-3"
            >
              <Sparkles className="size-6" />
              {isLoadingFinalAdvice ? '오케스트라가 한 줄 정리 중...' : '🎯 최종 조언 한 방 보기'}
              <Sparkles className="size-6" />
            </motion.span>
          </Button>
        </motion.div>
      )}

      <FinalAgentSummary agents={agents} onSave={onSave} />
    </div>
  );
}
