"use client";

import {
  CalendarDays,
  ExternalLink,
  FileText,
  Inbox,
  Link2,
  MessagesSquare,
  ShieldCheck,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMemo } from "react";
import {
  formatAbsoluteTime,
  formatRelativeTime,
} from "@/lib/relativeTime";
import {
  SOURCE_TYPE_LABEL,
  type Source,
  type SourceType,
} from "@/lib/types/source";

const TYPE_ICON: Record<SourceType, LucideIcon> = {
  notice: FileText,
  notice_pdf: FileText,
  mentoring: Users,
  application: Inbox,
  webex_message: MessagesSquare,
  webex_summary: MessagesSquare,
  calendar: CalendarDays,
  other: Link2,
};

const OFFICIAL_BADGE = {
  true: {
    chip:
      "border-blue-200 bg-blue-50 text-blue-700 hover:border-blue-300",
    badge: "bg-blue-600 text-white",
    label: "공식",
    icon: <ShieldCheck className="h-2.5 w-2.5" />,
    tooltipPrefix: "공식 출처",
  },
  false: {
    chip:
      "border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300",
    badge: "bg-slate-500 text-white",
    label: "참고",
    icon: null as React.ReactNode,
    tooltipPrefix: "비공식 출처 — 답변에 참고했지만 공식 채널은 아닙니다",
  },
} as const;

function buildTooltip(source: Source): string {
  const tone = OFFICIAL_BADGE[String(source.official) as "true" | "false"];
  const lines = [`[${tone.tooltipPrefix}]`, source.title];
  if (source.createdAt) {
    lines.push(`작성: ${formatAbsoluteTime(source.createdAt)}`);
  }
  if (source.collectedAt) {
    lines.push(`수집: ${formatAbsoluteTime(source.collectedAt)}`);
  }
  if (!source.url && source.rawRef) {
    lines.push(`참조: ${source.rawRef}`);
  }
  return lines.join("\n");
}

export function SourceChip({ source }: { source: Source }) {
  const tone = OFFICIAL_BADGE[String(source.official) as "true" | "false"];
  const TypeIcon = TYPE_ICON[source.type] ?? Link2;
  const isLink = Boolean(source.url);
  // source 참조가 바뀔 때만 tooltip 문자열 재계산 (파생 상태).
  const tooltip = useMemo(() => buildTooltip(source), [source]);

  const content = (
    <>
      <span
        className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold leading-none ${tone.badge}`}
        aria-label={`${tone.label} 출처`}
      >
        {tone.icon}
        {tone.label}
      </span>

      <span
        className="inline-flex items-center gap-1 text-[11px] text-current/70"
        aria-hidden="true"
      >
        <TypeIcon className="h-3 w-3" />
        {SOURCE_TYPE_LABEL[source.type]}
      </span>

      <span className="max-w-[180px] truncate text-current">
        {source.title}
      </span>

      {source.createdAt && (
        <span className="text-[11px] text-current/70">
          · {formatRelativeTime(source.createdAt)}
        </span>
      )}

      {isLink && <ExternalLink className="h-3 w-3 text-current/70" />}
    </>
  );

  const baseClass = `inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-medium transition ${tone.chip}`;

  if (isLink) {
    return (
      <a
        href={source.url}
        target="_blank"
        rel="noreferrer"
        title={tooltip}
        aria-label={`${tone.label} 출처: ${source.title}`}
        className={baseClass}
      >
        {content}
      </a>
    );
  }

  return (
    <span title={tooltip} className={baseClass}>
      {content}
    </span>
  );
}
