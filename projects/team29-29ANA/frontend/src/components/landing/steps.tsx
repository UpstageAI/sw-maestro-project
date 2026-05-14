"use client";

import { motion } from "motion/react";

const STEPS = [
  {
    number: "01",
    title: "자료 올리기",
    description:
      "자소서·이력서 PDF와 채용공고 텍스트, 회사명을 입력합니다. 회사명을 넣으면 인재상·기술 스택·최근 동향까지 자동으로 모아 컨텍스트로 사용합니다.",
  },
  {
    number: "02",
    title: "5~7개 질문에 답변",
    description:
      "다섯 카테고리(역량·경험·문제해결·협업·적합성)에서 균형 있게 묻고, 답변이 모호하면 꼬리질문으로 깊게 파고듭니다.",
  },
  {
    number: "03",
    title: "종합 리포트 확인",
    description:
      "전체 점수, 카테고리별 평균, 자주 드러난 약점 Top 5, 다음 면접에서 바꿀 행동까지 한 자리에서 받습니다.",
  },
];

export function Steps() {
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
            How it works
          </p>
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight sm:text-4xl">
            세 단계로 끝납니다.
          </h2>
        </motion.div>

        <ol className="grid grid-cols-1 gap-12 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <motion.li
              key={step.number}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.6, delay: i * 0.12 }}
              className="group flex flex-col gap-3"
            >
              <p className="font-mono text-xs text-muted-foreground transition-colors group-hover:text-primary">
                {step.number}
              </p>
              <h3 className="text-lg font-semibold tracking-tight">
                {step.title}
              </h3>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {step.description}
              </p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
