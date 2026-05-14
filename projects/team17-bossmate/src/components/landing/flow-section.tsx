"use client";

import { motion } from "motion/react";

const steps = [
  {
    n: "01",
    title: "가게 정보 입력",
    body: "가게명 / 업종 / 분위기 / 홍보 목적 / 상세 내용. 양식만 채우면 끝.",
  },
  {
    n: "02",
    title: "Solar 카피 작성",
    body: "Upstage Solar Pro 3 가 플랫폼별 글자수에 맞춰 SNS 캡션과 해시태그를 생성.",
  },
  {
    n: "03",
    title: "Azure 이미지 생성 + 검증",
    body: "GPT-Image-2 로 1장 합성 후 Upstage IE 가 핵심 키워드 누락을 검증해요.",
  },
  {
    n: "04",
    title: "PNG / 캡션 다운로드",
    body: "1080×1080 PNG 저장하고 SNS 캡션은 한 번에 복사. 피드백으로 재생성도 가능.",
  },
];

export function FlowSection() {
  return (
    <section id="flow" className="border-t border-border/60 bg-background">
      <div className="mx-auto w-full max-w-6xl px-5 py-24">
        <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-coral">
              만드는 법
            </p>
            <h2 className="text-balance mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
              네 단계, 1~2분이면 끝납니다.
            </h2>
          </div>
          <p className="max-w-sm text-sm text-muted-foreground">
            디자인 지식이 없어도 됩니다. Azure 키 미설정 시 이미지는 mock SVG 로
            대체되며 텍스트는 그대로 생성돼요.
          </p>
        </div>

        <ol className="relative mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <motion.li
              key={s.n}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.06, ease: "easeOut" }}
              className="relative rounded-3xl border border-border/70 bg-card p-6"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-widest text-brand-coral">
                STEP {s.n}
              </span>
              <h3 className="mt-3 font-display text-lg font-bold tracking-tight">
                {s.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {s.body}
              </p>
              {i < steps.length - 1 && (
                <span
                  aria-hidden
                  className="absolute right-4 top-6 hidden size-2 rounded-full bg-brand-coral/60 lg:block"
                />
              )}
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
