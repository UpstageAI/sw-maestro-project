"use client";

import { useState } from "react";
import type { Diary } from "@cat-dog-diary/shared-types";
import { DiaryDetailDialog } from "@/components/diary-detail-dialog";
import { MOOD_COLOR_VAR } from "@/lib/mood";

interface DiaryCardProps {
  diary: Diary;
}

const DATE_FMT = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  month: "long",
  day: "numeric",
});

export function DiaryCard({ diary }: DiaryCardProps) {
  const [open, setOpen] = useState(false);
  const dateLabel = DATE_FMT.format(new Date(diary.created_at));

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group/diary-card relative aspect-[3/4] w-72 shrink-0 overflow-hidden rounded-md text-left shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
        aria-label={`${diary.short_caption} 자세히 보기`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={diary.photo_signed_url}
          alt={diary.short_caption}
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover/diary-card:scale-[1.04]"
        />
        {/* gradient overlay — 하단 텍스트 가독성 */}
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-deep/85 via-deep/20 to-transparent"
        />
        {/* mood pill */}
        <span className="absolute top-4 right-4 inline-flex items-center gap-1.5 rounded-full bg-card/95 px-2.5 py-1 text-xs font-medium shadow-sm backdrop-blur-sm">
          <span
            className="size-1.5 rounded-full"
            style={{ backgroundColor: MOOD_COLOR_VAR[diary.mood_tag] }}
            aria-hidden
          />
          {diary.mood_tag}
        </span>
        {/* 하단 텍스트 */}
        <div className="absolute right-0 bottom-0 left-0 flex flex-col gap-1.5 p-5 text-background">
          <span className="text-xs tracking-wide opacity-70">{dateLabel}</span>
          <p className="line-clamp-2 text-base leading-snug font-medium">
            {diary.short_caption}
          </p>
        </div>
      </button>

      <DiaryDetailDialog diary={diary} open={open} onOpenChange={setOpen} />
    </>
  );
}
