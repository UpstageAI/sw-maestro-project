"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "motion/react";
import { Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(70% 60% at 70% 0%, color-mix(in oklch, var(--brand-blue) 18%, transparent), transparent 70%)",
        }}
      />
      <div className="mx-auto flex w-full max-w-5xl flex-col items-center px-5 pt-20 pb-24 text-center sm:pt-28 sm:pb-32">
        <motion.span
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2 rounded-full bg-brand-blue-soft px-3 py-1 text-xs font-semibold text-brand-blue-strong"
        >
          사장님을 위한 인스타 카드뉴스 도우미
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.05 }}
          className="text-balance mt-6 font-display text-[40px] font-extrabold leading-[1.1] tracking-tight text-foreground sm:text-6xl"
        >
          가게 정보만 입력하면,
          <br />
          홍보물이 완성돼요.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="mt-5 max-w-md text-base leading-relaxed text-muted-foreground sm:max-w-lg sm:text-lg"
        >
          가게 이름과 업종, 홍보 목적만 알려 주시면 인스타에 바로 올릴 수 있는
          카드뉴스 이미지와 홍보 문구, 해시태그까지 AI가 한 번에 만들어 드려요.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="mt-10 flex flex-col items-center gap-3"
        >
          <Button
            asChild
            size="lg"
            className="group h-16 rounded-2xl px-8 text-lg font-bold sm:h-[68px] sm:text-xl"
          >
            <Link href="/studio">
              <Sparkles className="size-6" />
              지금 홍보물 만들기
              <ArrowRight className="ml-1 size-5 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
          <p className="text-xs text-muted-foreground sm:text-sm">
            로그인 없이 무료로 사용해보실 수 있어요.
          </p>
        </motion.div>

        <HeroPreview />
      </div>
    </section>
  );
}

function HeroPreview() {
  const cards = [
    {
      title: "오늘은 한정 베이글",
      subtitle: "테디스 베이글",
      tag: "신메뉴",
      image: "/landing/card-new-menu.jpg",
      pill: "#191F28",
      pillFg: "#FFF7EC",
      accent: "#FF6B5B",
      rotate: -5,
      x: -16,
    },
    {
      title: "브런치 한 끼, 20%",
      subtitle: "카페 하루의 봄",
      tag: "이벤트",
      image: "/landing/card-event.jpg",
      pill: "#0F2235",
      pillFg: "#fff",
      accent: "#1A7A55",
      rotate: 4,
      x: 0,
    },
    {
      title: "정성 가득 한 끼",
      subtitle: "행복국밥",
      tag: "단골 후기",
      image: "/landing/card-review.jpg",
      pill: "#3A1F1F",
      pillFg: "#FFF1C9",
      accent: "#D83A26",
      rotate: -2,
      x: 16,
    },
  ];
  return (
    <div className="relative mt-16 grid w-full max-w-3xl grid-cols-3 gap-3 sm:gap-5">
      {cards.map((c, i) => (
        <motion.div
          key={c.title}
          initial={{ opacity: 0, y: 30, rotate: c.rotate * 1.4 }}
          animate={{ opacity: 1, y: 0, rotate: c.rotate }}
          whileHover={{ rotate: 0, y: -6 }}
          transition={{ duration: 0.6, delay: 0.4 + i * 0.08, ease: "easeOut" }}
          className="relative aspect-[3/4] overflow-hidden rounded-3xl border border-black/5 bg-muted toss-shadow"
          style={{
            transform: `translate(${c.x}px,0) rotate(${c.rotate}deg)`,
          }}
        >
          <Image
            src={c.image}
            alt={`${c.tag} — ${c.title}`}
            fill
            sizes="(max-width: 640px) 33vw, 220px"
            className="object-cover"
            priority={i < 2}
          />
          <div
            aria-hidden
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0) 35%, rgba(0,0,0,0.55) 100%)",
            }}
          />
          <div className="relative flex h-full flex-col gap-3 p-4 text-white sm:p-5">
            <span
              className="inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold tracking-wide sm:text-[11px]"
              style={{ background: c.pill, color: c.pillFg }}
            >
              <span
                className="size-1.5 rounded-full"
                style={{ background: c.accent }}
              />
              {c.tag}
            </span>
            <div className="mt-auto drop-shadow-[0_2px_8px_rgba(0,0,0,0.45)]">
              <p className="font-display text-sm font-extrabold leading-tight sm:text-lg">
                {c.title}
              </p>
              <p className="mt-1 text-[10px] font-medium text-white/85 sm:text-xs">
                {c.subtitle}
              </p>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
