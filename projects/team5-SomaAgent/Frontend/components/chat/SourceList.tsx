"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import type { Source } from "@/lib/types/source";
import { SourceChip } from "@/components/ui/SourceChip";

type Props = {
  sources: Source[];
  /** 비공식이 하나라도 있을 때 노출할 설명 배너 노출 여부 (default: true) */
  showUnofficialNotice?: boolean;
  /** true면 접힌 상태로 시작 (기본 true — 출처가 길 때 화면 점유 줄임) */
  defaultCollapsed?: boolean;
};

export function SourceList({
  sources,
  showUnofficialNotice = true,
  defaultCollapsed = true,
}: Props) {
  const [open, setOpen] = useState(!defaultCollapsed);

  if (!sources || sources.length === 0) return null;

  const hasUnofficial = sources.some((source) => !source.official);

  return (
    <details
      className="group rounded-xl border border-slate-200 bg-white/70 shadow-sm ring-1 ring-slate-100"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="flex list-none cursor-pointer select-none items-center justify-between gap-2 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500 [&::-webkit-details-marker]:hidden">
        <span>출처 · {sources.length}건</span>
        <ChevronDown className="h-4 w-4 shrink-0 text-slate-400 transition-transform group-open:rotate-180" />
      </summary>

      <div className="space-y-2 border-t border-slate-100 px-3 pb-3 pt-2">
        <ul className="flex flex-wrap gap-1.5">
          {sources.map((source, index) => (
            <li key={source.id ?? `${source.type}-${index}-${source.title}`}>
              <SourceChip source={source} />
            </li>
          ))}
        </ul>

        {showUnofficialNotice && hasUnofficial && (
          <p className="text-[11px] leading-relaxed text-slate-500">
            참고(회색) 출처는 공식 채널이 아닙니다. 답변 활용 시 공식 공지·시스템을
            한 번 더 확인해 주세요.
          </p>
        )}
      </div>
    </details>
  );
}
