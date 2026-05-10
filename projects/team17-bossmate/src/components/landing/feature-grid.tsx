"use client";

import { motion } from "motion/react";
import {
  Camera,
  Notebook,
  Wand2,
  Download,
} from "lucide-react";

const features = [
  {
    icon: Notebook,
    title: "양식만 채우면 끝",
    body:
      "가게명 / 업종 / 분위기 / 홍보 목적 / 상세 내용만 적어주세요. 사진 업로드는 필요 없어요.",
  },
  {
    icon: Wand2,
    title: "AI 에이전트가 1장 자동 합성",
    body:
      "Solar 카피 → Azure 이미지 → Upstage IE 검증까지 LangGraph 파이프라인이 한 번에 처리해요.",
  },
  {
    icon: Camera,
    title: "검증으로 키워드 누락 방지",
    body:
      "이미지에 가게명·핵심 키워드가 빠지면 자동 재시도. 누락된 항목은 결과 화면에 표시돼요.",
  },
  {
    icon: Download,
    title: "PNG 즉시 다운로드",
    body:
      "1080×1080 PNG로 저장하고 SNS 캡션은 한 번에 복사. 인스타 / 네이버 / 배민 모두 OK.",
  },
];

export function FeatureGrid() {
  return (
    <section id="features" className="border-t border-border/60 bg-background">
      <div className="mx-auto w-full max-w-6xl px-5 py-24">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-coral">
            왜 사장님메이트인가요
          </p>
          <h2 className="text-balance mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
            디자인 외주 안 맡겨도 돼요. <br className="hidden sm:block" />
            오늘 저녁 메뉴까지 카드뉴스로.
          </h2>
          <p className="mt-4 text-base text-muted-foreground">
            바쁜 사장님을 위한 미니 스튜디오. 가게 정보만 넣어주시면
            AI 에이전트가 카드 한 장과 SNS 캡션을 만들어 드려요.
          </p>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.55, delay: i * 0.06, ease: "easeOut" }}
              className="group relative overflow-hidden rounded-3xl border border-border/70 bg-card p-6"
            >
              <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-brand-coral/0 via-brand-coral to-brand-mint opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
              <f.icon className="size-6 text-brand-coral" strokeWidth={1.7} />
              <h3 className="mt-5 font-display text-lg font-bold tracking-tight">
                {f.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {f.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
