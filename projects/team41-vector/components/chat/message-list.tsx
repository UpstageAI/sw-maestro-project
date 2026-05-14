'use client';

// ─── MessageList ───
// 채팅 메시지 목록 전체를 담당한다.
// 메시지가 추가되거나 타이핑 중일 때 자동으로 맨 아래로 스크롤한다.
//
// 메시지마다 role에 따라 다른 카드/컴포넌트를 렌더링:
//   AI 메시지 아래에는 분석 결과로 생성된 카드들이 붙는다.
//   - categoryBreakdown: 카테고리 바 차트 (초기 분석 시만)
//   - simulation:        자산 시뮬레이션 라인 차트 (초기 분석 시만)
//   - mission:           미션 카드 (Coach가 미션 제안 시)
//   - dailySpending:     일별 소비 꺾은선 그래프 (get_daily_spending 툴 호출 시)

import { useEffect, useRef } from 'react';
import type { ChatMessage } from '@/lib/types';
import { MessageBubble } from './message-bubble';
import { TypingIndicator } from './typing-indicator';
import { PendingOrb } from './pending-orb';
import { SimulationChart } from './simulation-chart';
import { MissionCard } from './mission-card';
import { CategoryBreakdown } from './category-breakdown';
import { DailyChart } from './daily-chart';

type Props = {
  messages: ChatMessage[];
  isTyping: boolean;
  currentTypingId: string | null;
};

export function MessageList({ messages, isTyping, currentTypingId }: Props) {
  // 자동 스크롤용 앵커 div (목록 맨 끝에 위치)
  const anchorRef = useRef<HTMLDivElement | null>(null);

  // 메시지 추가, 타이핑 중 글자 추가, 인디케이터 표시 변화 시 스크롤
  const lastContent = messages[messages.length - 1]?.content ?? '';
  useEffect(() => {
    anchorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, lastContent, isTyping]);

  // 메시지가 없고 대기 중도 아니면 빈 상태 돼지저금통 표시
  if (messages.length === 0 && !isTyping) {
    return (
      <div className="flex-1 overflow-y-auto px-1 py-6">
        <div className="flex h-full items-center justify-center">
          <PendingOrb />
        </div>
      </div>
    );
  }

  // currentTypingId가 null이면 API 응답을 기다리는 중 → 점 3개 인디케이터 표시
  const showWaitingIndicator = isTyping && currentTypingId === null;

  return (
    <div className="flex-1 overflow-y-auto px-1 py-6">
      <div className="flex flex-col gap-4">
        {messages.map((m) => (
          <div key={m.id} className="flex flex-col gap-2">
            {/* 말풍선 */}
            <MessageBubble message={m} />

            {/* AI 메시지 아래에만 카드/차트 붙음 */}
            {m.role === 'ai' && m.categoryBreakdown && (
              <CategoryBreakdown data={m.categoryBreakdown} />
            )}
            {m.role === 'ai' && m.simulation && (
              <SimulationChart data={m.simulation} />
            )}
            {m.role === 'ai' && m.mission && (
              <MissionCard mission={m.mission} />
            )}
            {m.role === 'ai' && m.dailySpending && (
              <DailyChart data={m.dailySpending} />
            )}
          </div>
        ))}

        {/* API 응답 대기 중 점 3개 */}
        {showWaitingIndicator && <TypingIndicator />}

        {/* 자동 스크롤 앵커 */}
        <div ref={anchorRef} />
      </div>
    </div>
  );
}
