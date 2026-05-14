'use client';

import { useEffect, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { ArrowLeft, RotateCcw } from 'lucide-react';
import type { Agent, Punchline, PunchlineVibe } from '@/types';

interface FinalAdvicePhaseProps {
  agents: Agent[];
  punchline: Punchline;
  onBack: () => void;
  onReset: () => void;
}

// vibe별 배경 그라데이션과 강조 컬러.
const VIBE_THEME: Record<
  PunchlineVibe,
  { gradient: string; emoji: string; particle: string[] }
> = {
  harsh: {
    gradient: 'linear-gradient(135deg, oklch(0.45 0.25 25) 0%, oklch(0.3 0.15 15) 100%)',
    emoji: '🔥',
    particle: ['🔥', '💥', '⚡'],
  },
  hopeful: {
    gradient: 'linear-gradient(135deg, oklch(0.7 0.2 320) 0%, oklch(0.65 0.25 60) 100%)',
    emoji: '💖',
    particle: ['💖', '✨', '🌟'],
  },
  chaotic: {
    gradient: 'linear-gradient(135deg, oklch(0.7 0.2 60) 0%, oklch(0.65 0.22 320) 50%, oklch(0.62 0.18 200) 100%)',
    emoji: '🎉',
    particle: ['🎉', '🤡', '💫', '🌀'],
  },
  cold: {
    gradient: 'linear-gradient(135deg, oklch(0.4 0.15 230) 0%, oklch(0.3 0.1 220) 100%)',
    emoji: '❄️',
    particle: ['❄️', '🧊', '💧'],
  },
};

export function FinalAdvicePhase({ agents, punchline, onBack, onReset }: FinalAdvicePhaseProps) {
  const agent = agents.find((a) => a.id === punchline.chosenAgentId) ?? agents[0];
  const theme = VIBE_THEME[punchline.vibe];

  const topRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // 페이지 진입 시 부모 스크롤 컨테이너를 맨 위로.
    topRef.current?.scrollIntoView({ behavior: 'auto', block: 'start' });
  }, []);

  // 파티클 배치: 화면 곳곳에 랜덤(고정 시드)으로 흩뿌리기.
  const particles = useMemo(() => {
    const seed = punchline.oneLiner.length;
    const list: { left: number; top: number; emoji: string; delay: number; duration: number }[] = [];
    for (let i = 0; i < 24; i++) {
      const idx = (i * 31 + seed) % theme.particle.length;
      list.push({
        left: (i * 173) % 100,
        top: (i * 257) % 100,
        emoji: theme.particle[idx],
        delay: ((i * 13) % 10) / 10,
        duration: 2.5 + ((i * 7) % 20) / 10,
      });
    }
    return list;
  }, [punchline, theme]);

  return (
    <div
      ref={topRef}
      className="relative -m-6 flex min-h-[calc(100vh-8rem)] flex-col overflow-hidden rounded-2xl p-8"
      style={{ backgroundImage: theme.gradient }}
    >
      {/* 배경 파티클 (둥둥 떠다님) */}
      {particles.map((p, i) => (
        <motion.div
          key={i}
          className="pointer-events-none absolute select-none text-2xl opacity-60"
          style={{ left: `${p.left}%`, top: `${p.top}%` }}
          initial={{ y: 0, opacity: 0 }}
          animate={{ y: [-20, 20, -20], opacity: [0.2, 0.7, 0.2], rotate: [0, 360] }}
          transition={{ duration: p.duration, repeat: Infinity, delay: p.delay }}
        >
          {p.emoji}
        </motion.div>
      ))}

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-8 py-8">
        {/* 헤더 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-1"
        >
          <span className="text-sm font-semibold uppercase tracking-widest text-white/80">
            오케스트라의 한 줄 결론
          </span>
          <span className="text-xs text-white/60">최종 검토를 토대로 가장 어울리는 에이전트가 던지는 한 마디</span>
        </motion.div>

        {/* 에이전트 이미지 — 크고 펄스 */}
        <motion.div
          initial={{ scale: 0.5, opacity: 0, rotate: -10 }}
          animate={{ scale: 1, opacity: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 150, damping: 12, delay: 0.2 }}
          className="relative"
        >
          <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
            className="relative size-72 overflow-hidden rounded-[2.5rem] border-8 border-white shadow-2xl"
            style={{
              boxShadow: `0 0 60px 8px color-mix(in oklch, var(--${agent.colorKey}) 70%, transparent)`,
            }}
          >
            <img src={agent.image} alt={agent.name} className="size-full object-cover" draggable={false} />
          </motion.div>

          {/* 빙빙 도는 강조 이모지 */}
          <motion.div
            className="absolute -right-4 -top-4 text-5xl drop-shadow-lg"
            animate={{ rotate: [0, 360], scale: [1, 1.2, 1] }}
            transition={{ rotate: { duration: 4, repeat: Infinity, ease: 'linear' }, scale: { duration: 1.5, repeat: Infinity } }}
          >
            {theme.emoji}
          </motion.div>
        </motion.div>

        {/* 에이전트 이름 */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="text-2xl font-bold text-white/95 drop-shadow"
        >
          {agent.name}
        </motion.div>

        {/* 핵폭탄 한 줄 — 거대, 글로우, 살짝 흔들림 */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 10, delay: 0.9 }}
          className="px-4 text-center"
        >
          <motion.h1
            animate={{ x: [0, -2, 3, -2, 1, 0], textShadow: ['0 0 30px rgba(255,255,255,0.7)', '0 0 60px rgba(255,255,255,1)', '0 0 30px rgba(255,255,255,0.7)'] }}
            transition={{ x: { duration: 0.6, repeat: Infinity, repeatDelay: 1.4 }, textShadow: { duration: 2.5, repeat: Infinity } }}
            className="text-6xl font-black leading-tight text-white md:text-7xl lg:text-8xl"
            style={{
              WebkitTextStroke: '2px rgba(0,0,0,0.3)',
            }}
          >
            {punchline.oneLiner}
          </motion.h1>
        </motion.div>

        {/* 이유 (작게) */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 0.6 }}
          className="max-w-xl rounded-2xl bg-black/30 px-5 py-3 text-center text-base leading-relaxed text-white/90 backdrop-blur"
        >
          💬 {punchline.rationale}
        </motion.p>

        {/* 액션 버튼들 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.8, duration: 0.4 }}
          className="flex flex-wrap items-center justify-center gap-3 pt-2"
        >
          <Button variant="outline" className="bg-white/95 gap-2" onClick={onBack}>
            <ArrowLeft className="size-4" />
            최종 검토로 돌아가기
          </Button>
          <Button variant="outline" className="bg-white/95 gap-2" onClick={onReset}>
            <RotateCcw className="size-4" />
            새 상담 시작
          </Button>
        </motion.div>
      </div>
    </div>
  );
}
