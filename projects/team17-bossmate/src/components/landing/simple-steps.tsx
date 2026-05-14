"use client";

import { motion } from "motion/react";
import { ClipboardList, Sparkles, Download } from "lucide-react";

const steps = [
  {
    n: "1",
    icon: ClipboardList,
    title: "가게 정보를 적어요",
    body: "가게 이름, 업종, 홍보 목적, 원하는 분위기를 골라주세요.",
  },
  {
    n: "2",
    icon: Sparkles,
    title: "AI가 만들어요",
    body: "입력한 정보를 바탕으로 카드 이미지, 홍보 문구, 해시태그를 한 번에 만들어 드려요.",
  },
  {
    n: "3",
    icon: Download,
    title: "저장해서 올려요",
    body: "마음에 드는 카드를 PNG로 저장해서 인스타에 바로 올리세요.",
  },
];

export function SimpleSteps() {
  return (
    <section
      id="features"
      className="relative border-t border-border/60 bg-muted/40"
    >
      <div className="mx-auto w-full max-w-5xl px-5 py-24 sm:py-28">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-blue">
            만드는 법
          </p>
          <h2 className="text-balance mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
            세 단계면 끝나요.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-base text-muted-foreground">
            복잡한 디자인 도구 없이, 가게 정보만 있으면 충분해요.
          </p>
        </div>

        <ol className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {steps.map((s, i) => (
            <motion.li
              key={s.n}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.06, ease: "easeOut" }}
              className="relative rounded-3xl border border-border/70 bg-card p-6 toss-shadow"
            >
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-2xl bg-brand-blue text-white font-display font-extrabold">
                  {s.n}
                </span>
                <s.icon className="size-5 text-brand-blue" strokeWidth={2.2} />
              </div>
              <h3 className="mt-5 font-display text-lg font-bold tracking-tight">
                {s.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {s.body}
              </p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
