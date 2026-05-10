"use client";

import { motion } from "motion/react";

// 스크롤 lag 추가 절감: shadow-2xl → shadow-lg (paint 비용 ↓).
const baseCard =
  "absolute hidden sm:block rounded-2xl border border-border/50 bg-card/95 p-4 shadow-lg shadow-primary/10 [will-change:transform]";

export function FloatingCards() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-0">
      {/* 좌상단 — 메인 질문 */}
      <motion.div
        initial={{ opacity: 0, y: 30, rotate: 0 }}
        animate={{ opacity: 1, y: [0, -8, 0], rotate: -5 }}
        transition={{
          opacity: { duration: 0.8, delay: 0.4 },
          rotate: { duration: 0.8, delay: 0.4, ease: "easeOut" },
          y: { duration: 6, delay: 1.2, repeat: Infinity, ease: "easeInOut" },
        }}
        whileHover={{ y: -16, rotate: -2, scale: 1.04 }}
        className={`${baseCard} pointer-events-auto left-[6%] top-[20%] w-56`}
      >
        <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          메인 질문 · 역량
        </p>
        <p className="mt-2 text-sm font-medium leading-relaxed">
          가장 어려웠던 기술적 결정 하나만 들려주세요.
        </p>
      </motion.div>

      {/* 우상단 — 전체 점수 */}
      <motion.div
        initial={{ opacity: 0, y: 30, rotate: 0 }}
        animate={{ opacity: 1, y: [0, -10, 0], rotate: 6 }}
        transition={{
          opacity: { duration: 0.8, delay: 0.55 },
          rotate: { duration: 0.8, delay: 0.55, ease: "easeOut" },
          y: { duration: 7, delay: 1.5, repeat: Infinity, ease: "easeInOut" },
        }}
        whileHover={{ y: -18, rotate: 3, scale: 1.04 }}
        className={`${baseCard} pointer-events-auto right-[6%] top-[14%] w-48`}
      >
        <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          전체 점수
        </p>
        <p className="mt-2 flex items-baseline gap-1 text-3xl font-bold">
          3.42
          <span className="text-base font-normal text-muted-foreground">/5</span>
        </p>
        <div className="mt-3 grid grid-cols-5 gap-1">
          <div className="h-1 rounded-full bg-primary" />
          <div className="h-1 rounded-full bg-primary" />
          <div className="h-1 rounded-full bg-primary" />
          <div className="h-1 rounded-full bg-muted" />
          <div className="h-1 rounded-full bg-muted" />
        </div>
      </motion.div>

      {/* 좌하단 — 약점 태그 */}
      <motion.div
        initial={{ opacity: 0, y: 30, rotate: 0 }}
        animate={{ opacity: 1, y: [0, -6, 0], rotate: 3 }}
        transition={{
          opacity: { duration: 0.8, delay: 0.7 },
          rotate: { duration: 0.8, delay: 0.7, ease: "easeOut" },
          y: { duration: 5, delay: 1, repeat: Infinity, ease: "easeInOut" },
        }}
        whileHover={{ y: -14, rotate: 1, scale: 1.04 }}
        className={`${baseCard} pointer-events-auto left-[9%] bottom-[20%] w-52`}
      >
        <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          자주 드러난 약점
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <span className="rounded-full bg-warning/15 px-2.5 py-1 text-xs font-medium text-warning">
            구체성 부족
          </span>
          <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
            수치 인용
          </span>
        </div>
      </motion.div>

      {/* 우하단 — 꼬리질문 */}
      <motion.div
        initial={{ opacity: 0, y: 30, rotate: 0 }}
        animate={{ opacity: 1, y: [0, -9, 0], rotate: -4 }}
        transition={{
          opacity: { duration: 0.8, delay: 0.85 },
          rotate: { duration: 0.8, delay: 0.85, ease: "easeOut" },
          y: { duration: 6.5, delay: 1.3, repeat: Infinity, ease: "easeInOut" },
        }}
        whileHover={{ y: -16, rotate: -2, scale: 1.04 }}
        className={`${baseCard} pointer-events-auto right-[9%] bottom-[22%] w-56`}
      >
        <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          꼬리질문 · 역량
        </p>
        <p className="mt-2 text-sm font-medium leading-relaxed">
          왜 다른 대안이 아니라 그 선택이었나요?
        </p>
      </motion.div>
    </div>
  );
}
