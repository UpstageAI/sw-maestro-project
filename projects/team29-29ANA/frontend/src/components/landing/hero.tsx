"use client";

import Link from "next/link";
import { motion } from "motion/react";

import { Button } from "@/components/ui/button";
import { AmbientBackground } from "@/components/landing/ambient-background";
import { FloatingCards } from "@/components/landing/floating-cards";
import { FloatingIcons } from "@/components/landing/floating-icons";

export function Hero() {
  return (
    <section className="relative isolate overflow-hidden [contain:paint]">
      {/* Ambient — 면접 서비스 맞춤 모션 배경 */}
      <AmbientBackground />

      {/* Floating decoration — 면접 도형 + 결과 카드 */}
      <FloatingIcons />
      <FloatingCards />

      {/* Hero content */}
      <div className="relative mx-auto flex min-h-[88vh] w-full max-w-5xl flex-col items-center justify-center gap-8 px-4 py-32 text-center sm:px-6 sm:py-40">
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="text-5xl font-bold leading-[1.05] tracking-tight sm:text-7xl md:text-[5.5rem]"
        >
          내 회사에 맞춘
          <br />
          모의 면접.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg"
        >
          자소서와 채용공고만 있으면, 실제로 나올 법한 질문과 구조화된 답변
          피드백.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.4 }}
        >
          <Button
            asChild
            size="lg"
            className="rounded-full px-7 transition-transform hover:scale-105"
          >
            <Link href="/upload">Get started</Link>
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
