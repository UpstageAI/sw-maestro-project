'use client';

import { useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Swords, Trophy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UserInputBanner } from './UserInputBanner';
import type {
  Agent,
  AgentOpinion,
  DiscussionMessage,
  DiscussionRound as DiscussionRoundType,
  MessageType,
} from '@/types';

interface ChatItem {
  key: string;
  round: 1 | 2 | 3;
  type: MessageType;
  agentId: Agent['id'];
  content: string;
  replyToAgentId?: Agent['id'];
}

interface ChatPhaseProps {
  userInput: string;
  agents: Agent[];
  opinions: AgentOpinion[];
  rounds: DiscussionRoundType[];
  status: string | null;
  canReview: boolean;
  onFinalReview: () => void;
}

function buildItems(opinions: AgentOpinion[], rounds: DiscussionRoundType[]): ChatItem[] {
  const items: ChatItem[] = [];
  opinions.forEach((o, i) => {
    items.push({
      key: `r1-${o.agentId}-${i}`,
      round: 1,
      type: 'opinion',
      agentId: o.agentId,
      content: o.advice,
    });
  });
  rounds.forEach((r) => {
    const rn = (r.roundNumber === 1 ? 2 : 3) as 2 | 3;
    r.messages.forEach((m: DiscussionMessage, i: number) => {
      items.push({
        key: `r${rn}-${m.agentId}-${i}`,
        round: rn,
        type: m.messageType ?? (rn === 2 ? 'rebuttal' : 'deepdive'),
        agentId: m.agentId,
        content: m.content,
        replyToAgentId: m.replyToAgentId,
      });
    });
  });
  return items;
}

const ROUND_DIVIDER: Record<1 | 2 | 3, { icon: typeof Sparkles; title: string; subtitle: string }> = {
  1: {
    icon: Sparkles,
    title: '1라운드 — 각자 첫 의견',
    subtitle: '4명의 에이전트가 처음으로 의견을 던집니다',
  },
  2: {
    icon: Swords,
    title: '2라운드 — 뚜까팸 시작! 💥',
    subtitle: '서로 약점을 짚으며 정면으로 반박합니다',
  },
  3: {
    icon: Trophy,
    title: '3라운드 — 최종 한 방 🥊',
    subtitle: '끝까지 자기 입장을 고수하며 마지막 반박',
  },
};

export function ChatPhase({
  userInput,
  agents,
  opinions,
  rounds,
  status,
  canReview,
  onFinalReview,
}: ChatPhaseProps) {
  const items = useMemo(() => buildItems(opinions, rounds), [opinions, rounds]);
  const agentMap = useMemo(() => new Map(agents.map((a) => [a.id, a])), [agents]);

  const bottomRef = useRef<HTMLDivElement>(null);

  // 새 메시지 도착 시 부드럽게 맨 아래로 스크롤 (부모 스크롤 컨테이너 기준).
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [items.length]);

  // 표시할 라운드 디바이더 (해당 라운드의 메시지가 1개 이상 있을 때만).
  const roundsPresent = useMemo(() => {
    const set = new Set<1 | 2 | 3>();
    items.forEach((i) => set.add(i.round));
    return set;
  }, [items]);

  let lastRound: 0 | 1 | 2 | 3 = 0;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <UserInputBanner userInput={userInput} />

      <AnimatePresence initial={false}>
        {items.map((item) => {
          const agent = agentMap.get(item.agentId);
          if (!agent) return null;
          const replyToAgent =
            item.replyToAgentId && item.replyToAgentId !== item.agentId
              ? agentMap.get(item.replyToAgentId)
              : undefined;
          const showDivider = item.round !== lastRound;
          lastRound = item.round;

          return (
            <div key={item.key} className="flex flex-col gap-3">
              {showDivider && roundsPresent.has(item.round) && (
                <RoundDivider round={item.round} />
              )}
              <ChatRow agent={agent} item={item} replyToAgent={replyToAgent} />
            </div>
          );
        })}
      </AnimatePresence>

      {/* 진행 중 표시 */}
      {!canReview && items.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-2 self-center py-2 text-sm text-muted-foreground"
        >
          <span className="size-2.5 animate-pulse rounded-full bg-primary" />
          {statusLabel(status)}
        </motion.div>
      )}

      {/* 하단 "최종 검토" 버튼 */}
      <div className="sticky bottom-0 -mx-4 mt-4 border-t bg-white/95 px-4 py-3 backdrop-blur">
        <Button
          className="mx-auto block w-full max-w-md gap-2"
          onClick={onFinalReview}
          disabled={!canReview}
          size="lg"
        >
          {canReview ? '최종 검토 보러가기' : '에이전트들이 토론 중...'}
        </Button>
      </div>

      <div ref={bottomRef} />
    </div>
  );
}

function statusLabel(status: string | null): string {
  switch (status) {
    case 'pending':
      return '준비 중...';
    case 'analyzing':
      return '슈퍼바이저가 고민을 분석 중...';
    case 'round_1_running':
      return '4명이 첫 의견을 작성 중...';
    case 'summary_1_running':
      return '쟁점 정리 중...';
    case 'round_2_running':
      return '뚜까팸 라운드 진행 중...';
    case 'classify_2_running':
      return '충돌 분류 중...';
    case 'round_3_running':
      return '최종 한 방 준비 중...';
    case 'summarizing':
      return '최종 결론 작성 중...';
    default:
      return '진행 중...';
  }
}

function RoundDivider({ round }: { round: 1 | 2 | 3 }) {
  const { icon: Icon, title, subtitle } = ROUND_DIVIDER[round];
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="my-4 flex items-center gap-3"
    >
      <span className="h-px flex-1 bg-border" />
      <div className="flex items-center gap-2.5 rounded-full bg-primary/10 px-5 py-2.5 text-primary">
        <Icon className="size-5" />
        <div className="flex flex-col">
          <span className="text-sm font-bold leading-tight">{title}</span>
          <span className="text-xs leading-tight text-primary/70">{subtitle}</span>
        </div>
      </div>
      <span className="h-px flex-1 bg-border" />
    </motion.div>
  );
}

interface ChatRowProps {
  agent: Agent;
  item: ChatItem;
  replyToAgent?: Agent;
}

function ChatRow({ agent, item, replyToAgent }: ChatRowProps) {
  const isRebuttal = item.round >= 2;
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={
        isRebuttal
          ? {
              opacity: 1,
              y: 0,
              x: [0, -10, 10, -6, 4, 0],
            }
          : { opacity: 1, y: 0 }
      }
      transition={{ duration: isRebuttal ? 0.6 : 0.35, ease: 'easeOut' }}
      className="flex items-start gap-4"
    >
      {/* 에이전트 대표 이미지 */}
      <div
        className="relative shrink-0 overflow-hidden rounded-3xl"
        style={{
          width: 200,
          height: 200,
          outline: `5px solid color-mix(in oklch, var(--${agent.colorKey}) 60%, white)`,
        }}
      >
        <img
          src={agent.image}
          alt={agent.name}
          className="size-full object-cover"
          draggable={false}
        />
        {isRebuttal && (
          <motion.div
            className="pointer-events-none absolute -right-3 -top-3 text-6xl"
            initial={{ scale: 0, rotate: -30, opacity: 0 }}
            animate={{
              scale: [0, 1.6, 1.2, 1.3, 0],
              rotate: [-30, 0, -10, 5, 20],
              opacity: [0, 1, 1, 1, 0],
            }}
            transition={{ duration: 1.4, times: [0, 0.2, 0.5, 0.8, 1], delay: 0.2 }}
          >
            💥
          </motion.div>
        )}
      </div>

      {/* 말풍선 */}
      <div className="flex flex-1 flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-lg font-bold">{agent.name}</span>
          {replyToAgent && (
            <>
              <motion.span
                className="inline-block text-2xl"
                initial={{ scale: 0.6 }}
                animate={{ scale: [0.6, 1.6, 1] }}
                transition={{ duration: 0.45, delay: 0.25 }}
                aria-label="반박"
              >
                👊
              </motion.span>
              <span
                className="rounded-md px-2.5 py-1 text-sm font-semibold"
                style={{
                  backgroundColor: `color-mix(in oklch, var(--${replyToAgent.colorKey}) 18%, white)`,
                  color: `var(--${replyToAgent.colorKey})`,
                }}
                title={`${replyToAgent.name}을(를) 반박합니다`}
              >
                {replyToAgent.name}
              </span>
            </>
          )}
        </div>
        <div
          className="rounded-2xl rounded-tl-sm border-2 px-5 py-4 text-base leading-relaxed shadow-sm"
          style={{
            backgroundColor: `color-mix(in oklch, var(--${agent.colorKey}) 8%, white)`,
            borderColor: `color-mix(in oklch, var(--${agent.colorKey}) 25%, white)`,
          }}
        >
          {item.content}
        </div>
      </div>
    </motion.div>
  );
}
