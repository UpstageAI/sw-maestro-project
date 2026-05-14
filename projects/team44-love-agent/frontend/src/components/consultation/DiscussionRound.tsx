import { motion } from 'framer-motion';
import type { Agent, DiscussionRound as DiscussionRoundType } from '@/types';
import { AgentCard } from '@/components/agents';

interface DiscussionRoundProps {
  round: DiscussionRoundType;
  agents: Agent[];
}

export function DiscussionRound({ round, agents }: DiscussionRoundProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {round.messages.map((message, i) => {
        const agent = agents.find((a) => a.id === message.agentId);
        if (!agent) return null;
        // 자기 자신 참조는 표시하지 않음 (의미 없음).
        const replyToAgent =
          message.replyToAgentId && message.replyToAgentId !== message.agentId
            ? agents.find((a) => a.id === message.replyToAgentId)
            : undefined;
        return (
          <motion.div
            key={i}
            className="h-full"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07, duration: 0.3, ease: 'easeOut' }}
          >
            <AgentCard agent={agent} message={message} replyToAgent={replyToAgent} />
          </motion.div>
        );
      })}
    </div>
  );
}
