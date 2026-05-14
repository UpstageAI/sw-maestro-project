"use client";

import { motion } from "motion/react";

/**
 * 면접 서비스용 ambient 배경.
 * - 미묘한 그리드 (radial fade)
 * - 중앙 큰 글로우(호흡)
 * - 좌우 드리프트 보조 글로우
 * - 상단 빛나는 호 — 진입 1회 페이드 후 끊김 없는 무한 흐름
 * - 하단에서 위로 천천히 올라가는 입자
 */
export function AmbientBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
    >
      {/* 1. 미묘한 그리드 — radial mask 제거(GPU 합성 비용 ↓), opacity 만 낮춰 가장자리 자연스럽게 처리 */}
      <div className="absolute inset-0 bg-grid opacity-25 dark:opacity-30" />

      {/* 2. 중앙 글로우 — 매우 느린 호흡(10s)으로 frame당 비용 ↓ */}
      <motion.div
        animate={{ opacity: [0.75, 1, 0.75] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        className="absolute left-1/2 top-[42%] size-[700px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/15 blur-[60px] [will-change:opacity] dark:bg-primary/35"
      />

      {/* 3. 보조 글로우 1개 — drift motion 제거, 정적 (시각 거의 동일하지만 paint 비용 큰 감소) */}
      <div className="absolute right-[8%] top-[8%] size-[380px] rounded-full bg-accent/15 blur-[60px] dark:bg-accent/30" />

      {/* 4. 빛나는 호 */}
      <ArcBeam />

      {/* 5. 떠오르는 입자 */}
      <Particles />
    </div>
  );
}

function ArcBeam() {
  return (
    <svg
      className="absolute left-1/2 top-[8%] h-[600px] w-[1400px] -translate-x-1/2"
      viewBox="0 0 1400 600"
      fill="none"
    >
      <defs>
        <linearGradient id="arc-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="oklch(0.621 0.211 259)" stopOpacity="0" />
          <stop offset="50%" stopColor="oklch(0.621 0.211 259)" stopOpacity="1" />
          <stop offset="100%" stopColor="oklch(0.621 0.211 259)" stopOpacity="0" />
        </linearGradient>
        {/* SVG glow filter 자체 제거 — 스크롤 시 SVG filter 가 매 프레임 재계산되어 비용 큼.
           외곽 호는 stroke-width 와 그라디언트만으로도 충분히 발광 효과를 냄. */}
      </defs>

      {/* 외곽 호 — 진입 시 그려진 뒤 정적 */}
      <motion.path
        d="M 0 500 Q 700 50 1400 500"
        stroke="url(#arc-gradient)"
        strokeWidth="3"
        fill="none"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 0.8 }}
        transition={{
          pathLength: { duration: 2.4, ease: [0.16, 1, 0.3, 1] },
          opacity: { duration: 1.6, ease: "easeOut", delay: 0.2 },
        }}
      />

      {/* 흐르는 빛 — 외곽 호가 그려진 뒤 페이드인, 그 후 끊김 없는 무한 흐름 */}
      <motion.g
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.2, ease: "easeOut", delay: 2 }}
      >
        <motion.path
          d="M 0 500 Q 700 50 1400 500"
          pathLength={100}
          stroke="oklch(0.95 0.05 250)"
          strokeWidth="2"
          fill="none"
          strokeLinecap="round"
          strokeDasharray="14 86"
            initial={{ strokeDashoffset: 0 }}
          animate={{ strokeDashoffset: -100 }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      </motion.g>
    </svg>
  );
}

// 입자 7→4 (분위기는 살리되 동시 무한 루프 더 줄임)
const PARTICLES = [
  { x: "16%", delay: 0, dur: 11, size: 1 },
  { x: "38%", delay: 3.5, dur: 12, size: 1.5 },
  { x: "62%", delay: 1.5, dur: 10.5, size: 1 },
  { x: "84%", delay: 5, dur: 11.5, size: 1.5 },
];

function Particles() {
  return (
    <>
      {PARTICLES.map((p, i) => (
        <motion.div
          key={i}
          initial={{ y: "100vh", opacity: 0 }}
          animate={{
            y: "-15vh",
            opacity: [0, 0.7, 0.7, 0],
          }}
          transition={{
            duration: p.dur,
            delay: p.delay,
            repeat: Infinity,
            ease: "linear",
          }}
          style={{
            left: p.x,
            width: `${p.size * 4}px`,
            height: `${p.size * 4}px`,
          }}
          className="absolute rounded-full bg-foreground/50 shadow-[0_0_6px_currentColor] [will-change:transform,opacity] dark:bg-foreground/70"
        />
      ))}
    </>
  );
}
