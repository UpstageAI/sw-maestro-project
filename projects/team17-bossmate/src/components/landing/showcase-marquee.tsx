"use client";

import { motion } from "motion/react";

const SHOWCASE = [
  {
    title: "오늘은 한정 베이글",
    sub: "테디스 베이글",
    badge: "신메뉴",
    bg: "linear-gradient(135deg,#fff7ec,#ffd5be)",
    accent: "#ff6b5b",
    pill: "#1d1f3a",
  },
  {
    title: "브런치 한 끼, 20%",
    sub: "카페 하루의 봄",
    badge: "이벤트",
    bg: "linear-gradient(135deg,#e8f5ee,#bfe0cf)",
    accent: "#1a7a55",
    pill: "#0f2235",
  },
  {
    title: "어버이날 카네이션 예약",
    sub: "꽃집 다정",
    badge: "기간 한정",
    bg: "linear-gradient(135deg,#eaf3ff,#fcd1e2)",
    accent: "#e84a8d",
    pill: "#21314d",
  },
  {
    title: "봄맞이 헤어 추천",
    sub: "헤어룸 라온",
    badge: "단골 후기",
    bg: "linear-gradient(135deg,#ece4d2,#cdb98a)",
    accent: "#7e6240",
    pill: "#1a1a1a",
  },
  {
    title: "화덕 피자 새 메뉴",
    sub: "피자 노바",
    badge: "신메뉴",
    bg: "linear-gradient(135deg,#fff1c9,#ffb88a)",
    accent: "#d83a26",
    pill: "#3a1f1f",
  },
  {
    title: "딸기 시즌 20% 할인",
    sub: "디저트 살롱 모리",
    badge: "이벤트",
    bg: "linear-gradient(135deg,#fde2e7,#f5b8c5)",
    accent: "#d32d6c",
    pill: "#3a1626",
  },
];

export function ShowcaseMarquee() {
  const doubled = [...SHOWCASE, ...SHOWCASE];
  return (
    <section
      id="showcase"
      className="relative overflow-hidden border-t border-border/60 bg-[color:var(--brand-cream)]"
    >
      <div className="mx-auto w-full max-w-6xl px-5 pt-20 pb-6">
        <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-coral">
              실사용 쇼케이스
            </p>
            <h2 className="text-balance mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
              사장님 가게마다 톤은 달라야죠. <br className="hidden sm:block" />
              사장님메이트는 6가지 무드를 자동 추천해요.
            </h2>
          </div>
          <p className="max-w-xs text-sm text-muted-foreground">
            사장님메이트의 단일 카드 출력 예시입니다. 이미지는 mock SVG 로 대체.
          </p>
        </div>
      </div>

      <div className="relative pb-24 [mask-image:linear-gradient(to_right,transparent,#000_8%,#000_92%,transparent)]">
        <motion.div
          className="flex w-max gap-5 px-5 will-change-transform animate-marquee"
        >
          {doubled.map((c, i) => (
            <article
              key={`${c.title}-${i}`}
              className="relative flex h-72 w-56 shrink-0 flex-col overflow-hidden rounded-3xl border border-black/5 p-5 shadow-[0_24px_60px_-30px_rgba(20,30,50,0.35)]"
              style={{ background: c.bg }}
            >
              <span
                className="inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold"
                style={{ background: c.pill, color: "#fff" }}
              >
                <span
                  className="size-1.5 rounded-full"
                  style={{ background: c.accent }}
                />
                {c.badge}
              </span>
              <div className="mt-auto">
                <p className="font-display text-xl font-extrabold leading-tight text-[color:var(--brand-navy)]">
                  {c.title}
                </p>
                <p className="mt-1 text-[11px] font-medium text-black/55">
                  BY {c.sub}
                </p>
              </div>
            </article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
