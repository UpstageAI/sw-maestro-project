"use client";

import { motion } from "motion/react";

const AXES = [
  {
    name: "STAR 구조",
    short: "Situation · Task · Action · Result",
    desc: "상황·과제·행동·결과의 네 단계로 답변이 흐르는지. 단계가 빠지면 면접관은 맥락을 잡기 어렵습니다.",
  },
  {
    name: "구체성",
    short: "Specificity",
    desc: "수치, 기간, 역할, 기술 이름처럼 검증 가능한 디테일이 있는지. '많이 개선했다'보다 '처리량 5배'.",
  },
  {
    name: "직무 관련성",
    short: "Relevance",
    desc: "지원 직무·회사 키워드가 답변에 자연스럽게 녹아 있는지. 일반론으로만 흐르지 않는지.",
  },
  {
    name: "일관성",
    short: "Consistency",
    desc: "자소서·이력서·이전 답변과 모순 없이 한 흐름으로 이어지는지. 세부가 어긋나면 신뢰가 떨어집니다.",
  },
];

export function EvaluationAxes() {
  return (
    <section className="border-t border-border/60">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-12 px-4 py-24 sm:px-6 sm:py-32">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="flex flex-col gap-3"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            How we evaluate
          </p>
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight sm:text-4xl">
            네 가지 축으로 답변을 진단합니다.
          </h2>
          <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
            각 답변마다 1~5점으로 평가하고, 자주 드러나는 약점을 태그로 모아
            종합 리포트에서 우선순위와 함께 보여드립니다.
          </p>
        </motion.div>

        <ol className="grid grid-cols-1 gap-x-12 gap-y-10 sm:grid-cols-2">
          {AXES.map((a, i) => (
            <motion.li
              key={a.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="flex flex-col gap-2"
            >
              <div className="flex flex-wrap items-baseline gap-3">
                <h3 className="text-lg font-semibold tracking-tight">
                  {a.name}
                </h3>
                <p className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
                  {a.short}
                </p>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {a.desc}
              </p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
