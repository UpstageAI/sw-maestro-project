"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function LandingCTA() {
  return (
    <section className="border-t border-border/60 bg-background">
      <div className="mx-auto flex w-full max-w-5xl flex-col items-center gap-6 px-5 py-24 text-center sm:py-28">
        <motion.h2
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className="text-balance font-display text-3xl font-extrabold tracking-tight sm:text-4xl"
        >
          오늘 한 끼, 카드뉴스로 알려보세요.
        </motion.h2>
        <p className="max-w-md text-base text-muted-foreground">
          1분이면 인스타에 올릴 카드 한 장과 SNS 캡션이 손에 들어옵니다.
        </p>
        <Button
          asChild
          size="lg"
          className="h-14 rounded-2xl px-7 text-lg font-bold sm:h-16 sm:text-xl"
        >
          <Link href="/studio">
            지금 시작하기
            <ArrowRight className="ml-1 size-5" />
          </Link>
        </Button>
      </div>
    </section>
  );
}
