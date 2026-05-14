"use client";

import { Award, CheckCircle2, Clock, MessageCircle, Mic, Star } from "lucide-react";
import { motion } from "motion/react";

const ITEMS = [
  // 면접의 시작 — 마이크
  {
    Icon: Mic,
    pos: "left-[8%] top-[12%]",
    rotate: -8,
    delay: 0.25,
    duration: 5.5,
    tint: "from-primary/30 to-primary/5",
    iconClass: "text-primary",
  },
  // 시간 제한
  {
    Icon: Clock,
    pos: "right-[16%] top-[8%]",
    rotate: 6,
    delay: 0.4,
    duration: 6.5,
    tint: "from-accent/25 to-accent/5",
    iconClass: "text-accent",
  },
  // 평가
  {
    Icon: Star,
    pos: "right-[3%] top-[42%]",
    rotate: -5,
    delay: 0.6,
    duration: 5.2,
    tint: "from-warning/30 to-warning/5",
    iconClass: "text-warning",
  },
  // 통과 / 체크
  {
    Icon: CheckCircle2,
    pos: "left-[3%] top-[50%]",
    rotate: 4,
    delay: 0.55,
    duration: 6,
    tint: "from-success/30 to-success/5",
    iconClass: "text-success",
  },
  // 답변 / 대화
  {
    Icon: MessageCircle,
    pos: "right-[20%] bottom-[10%]",
    rotate: -7,
    delay: 0.95,
    duration: 6.2,
    tint: "from-primary/25 to-primary/5",
    iconClass: "text-primary",
  },
  // 트로피
  {
    Icon: Award,
    pos: "left-[24%] bottom-[8%]",
    rotate: 5,
    delay: 1.05,
    duration: 5.8,
    tint: "from-accent/25 to-accent/5",
    iconClass: "text-accent",
  },
];

export function FloatingIcons() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 -z-0 hidden md:block"
    >
      {ITEMS.map(({ Icon, pos, rotate, delay, duration, tint, iconClass }, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, scale: 0.6, rotate: 0 }}
          animate={{
            opacity: 1,
            scale: 1,
            y: [0, -12, 0],
            rotate,
          }}
          transition={{
            opacity: { duration: 0.7, delay, ease: "easeOut" },
            scale: { duration: 0.7, delay, ease: "easeOut" },
            rotate: { duration: 0.7, delay, ease: "easeOut" },
            y: {
              duration,
              repeat: Infinity,
              ease: "easeInOut",
              delay: delay + 0.6,
            },
          }}
          className={`absolute ${pos} flex size-14 items-center justify-center rounded-2xl border border-border/40 bg-gradient-to-br ${tint} shadow-md shadow-primary/10 [will-change:transform]`}
        >
          <Icon className={`size-6 ${iconClass}`} strokeWidth={1.75} />
        </motion.div>
      ))}
    </div>
  );
}
