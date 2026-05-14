"use client";

import { motion } from "motion/react";

const POINTS = [
  {
    quote: "내 답변이 좋은 답변인지 모르겠다.",
    desc: "혼자 연습하면 피드백이 없습니다. 무엇이 강하고 무엇이 부족한지 짚어주는 사람이 필요합니다.",
  },
  {
    quote: "회사마다 어떤 질문이 나올지 가늠이 안 된다.",
    desc: "일반 질문집은 회사·직무 특수성을 반영하지 못합니다. 지원하는 곳에 맞춘 질문이 필요합니다.",
  },
];

export function PainPoints() {
  return (
    <section className="border-t border-border/60 bg-muted/30">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-12 px-4 py-24 sm:px-6 sm:py-32">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="flex flex-col gap-3"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            For 취업 준비생
          </p>
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight sm:text-4xl">
            혼자 연습하다 막히는 두 가지.
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 gap-12 sm:grid-cols-2">
          {POINTS.map((p, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.6, delay: i * 0.12 }}
              className="flex flex-col gap-3"
            >
              <p className="text-lg font-semibold leading-snug">{p.quote}</p>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {p.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
