'use client';

import { motion } from 'framer-motion';
import type { Agent, AgentOpinion, DiscussionMessage } from '@/types';
import { MESSAGE_TYPE_LABEL } from '@/types';
import { AgentAvatar } from './AgentAvatar';

interface AgentCardProps {
  agent: Agent;
  opinion?: AgentOpinion;
  message?: DiscussionMessage;
  // 반박/보완 대상 에이전트 (토론 라운드용). 있으면 헤더에 "→ 이름" + 공격 모션.
  replyToAgent?: Agent;
}

export function AgentCard({ agent, opinion, message, replyToAgent }: AgentCardProps) {
  const content = opinion?.advice ?? message?.content;
  const messageType = message?.messageType;
  const label =
    messageType && messageType !== 'opinion' ? MESSAGE_TYPE_LABEL[messageType] : undefined;
  const isAttacking = !!replyToAgent;

  return (
    <motion.div
      className="relative flex h-full flex-col gap-3 rounded-xl p-4"
      style={{ backgroundColor: `color-mix(in oklch, var(--${agent.colorKey}) 10%, white)` }}
      // 공격 모션: 마운트 시 한 번 흔들면서 살짝 앞으로 튕긴다.
      animate={
        isAttacking
          ? {
              x: [0, -8, 10, -6, 4, 0],
              rotate: [0, -1.5, 2, -1, 0.5, 0],
              boxShadow: [
                '0 0 0 0 rgba(0,0,0,0)',
                `0 0 0 4px color-mix(in oklch, var(--${agent.colorKey}) 35%, transparent)`,
                '0 0 0 0 rgba(0,0,0,0)',
              ],
            }
          : undefined
      }
      transition={{
        duration: 0.6,
        ease: 'easeOut',
        delay: 0.15,
      }}
    >
      {/* 충격 이모지 — 반박 카드에만, 마운트 시 한 번 튀어 오른다 */}
      {isAttacking && (
        <motion.div
          className="pointer-events-none absolute -right-3 -top-3 z-10 select-none text-3xl"
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

      {/* 헤더 */}
      <div className="flex items-center gap-2.5">
        <AgentAvatar agentId={agent.id} name={agent.name} colorKey={agent.colorKey} size="md" />
        <div className="flex flex-1 flex-col gap-0.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-sm font-semibold">{agent.name}</span>
            {replyToAgent && (
              <>
                <motion.span
                  className="inline-block text-base"
                  initial={{ scale: 0.6 }}
                  animate={{ scale: [0.6, 1.6, 1] }}
                  transition={{ duration: 0.45, delay: 0.25, times: [0, 0.5, 1] }}
                  aria-label="반박"
                >
                  👊
                </motion.span>
                <span
                  className="rounded-md px-2 py-0.5 text-xs font-medium"
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
          <span className="text-xs text-muted-foreground">{agent.persona}</span>
        </div>
        {/* 라벨 배지 */}
        {label && (
          <span
            className="rounded-md px-3 py-1 text-xs font-semibold"
            style={{
              backgroundColor: `color-mix(in oklch, var(--${agent.colorKey}) 20%, white)`,
              color: `var(--${agent.colorKey})`,
            }}
          >
            {label}
          </span>
        )}
      </div>

      {/* 본문 */}
      {content && <p className="flex-1 text-sm leading-relaxed">{content}</p>}
    </motion.div>
  );
}
