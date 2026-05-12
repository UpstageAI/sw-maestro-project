"use client";

import Link from "next/link";
import { motion } from "motion/react";

import { Button } from "@/components/ui/button";

export function ClosingCTA() {
  return (
    <section className="border-t border-border/60 bg-muted/30">
      <div className="mx-auto flex w-full max-w-5xl flex-col items-start gap-6 px-4 py-24 sm:px-6 sm:py-32">
        <motion.h2
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="text-3xl font-semibold tracking-tight sm:text-4xl"
        >
          지금 시작해보세요.
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="max-w-md text-sm leading-relaxed text-muted-foreground"
        >
          PDF 두 장과 채용공고 텍스트면 됩니다. 5~7개 질문 후 종합 리포트가
          나옵니다.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, delay: 0.2 }}
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
