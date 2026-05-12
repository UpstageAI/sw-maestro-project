"use client";

import {
  Hash,
  MessagesSquare,
  ShieldOff,
  TriangleAlert,
  Users,
} from "lucide-react";
import { useMemo } from "react";
import {
  formatAbsoluteTime,
  formatRelativeTime,
} from "@/lib/relativeTime";
import {
  groupWebexByRoom,
  type WebexHighlight,
  type WebexRoomGroup,
  type WebexSummaryItem,
} from "@/lib/types/webex";

type Props = {
  items: WebexSummaryItem[];
};

export function WebexSummary({ items }: Props) {
  // items 참조가 바뀔 때만 룸별 그룹핑 비용을 다시 치름 (파생 상태).
  const groups = useMemo(() => groupWebexByRoom(items), [items]);

  return (
    <div className="space-y-3">
      <UnofficialBanner />
      {groups.map((group) => (
        <RoomGroup key={group.roomId} group={group} />
      ))}
    </div>
  );
}

function UnofficialBanner() {
  return (
    <div
      role="note"
      aria-label="비공식 출처 안내"
      className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800"
    >
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="leading-relaxed">
        <p className="font-semibold">Webex 공유 스페이스 — 비공식 출처</p>
        <p className="mt-0.5 text-amber-700">
          팀 채팅에서 수집한 데이터예요. 공식 공지·시스템과 다를 수 있으니 활용
          전에 한 번 더 확인해 주세요.
        </p>
      </div>
    </div>
  );
}

function RoomGroup({ group }: { group: WebexRoomGroup }) {
  return (
    <section
      aria-label={`Webex 룸 ${group.roomName} 요약`}
      className="overflow-hidden rounded-xl border border-slate-200 bg-white"
    >
      <header className="flex items-center justify-between gap-2 border-b border-slate-100 bg-slate-50/70 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-amber-100 text-amber-700">
            <MessagesSquare className="h-3.5 w-3.5" />
          </span>
          <p className="truncate text-sm font-semibold text-slate-800">
            {group.roomName}
          </p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
          <Hash className="h-3 w-3" />
          {group.items.length}건
        </span>
      </header>

      <ul className="divide-y divide-slate-100">
        {group.items.map((item) => (
          <li key={item.id}>
            <SummaryRow item={item} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function SummaryRow({ item }: { item: WebexSummaryItem }) {
  return (
    <article className="space-y-2 px-3 py-3">
      <header>
        <h4 className="text-sm font-semibold text-slate-900">{item.topic}</h4>
        <p className="mt-0.5 text-xs leading-relaxed text-slate-600">
          {item.summary}
        </p>
      </header>

      {item.highlights && item.highlights.length > 0 && (
        <ul className="space-y-1.5">
          {item.highlights.map((highlight, index) => (
            <li
              key={highlight.id ?? `${item.id}-h-${index}`}
              className="rounded-lg border border-slate-100 bg-slate-50/60 px-2.5 py-1.5"
            >
              <Highlight highlight={highlight} />
            </li>
          ))}
        </ul>
      )}

      <SummaryFooter item={item} />
    </article>
  );
}

function Highlight({ highlight }: { highlight: WebexHighlight }) {
  return (
    <div className="text-xs">
      <div className="flex items-center justify-between text-slate-500">
        <span className="font-medium text-slate-700">{highlight.author}</span>
        {highlight.createdAt && (
          <span title={formatAbsoluteTime(highlight.createdAt)}>
            {formatRelativeTime(highlight.createdAt)}
          </span>
        )}
      </div>
      <p className="mt-0.5 leading-relaxed text-slate-700">
        “{highlight.text}”
      </p>
    </div>
  );
}

function SummaryFooter({ item }: { item: WebexSummaryItem }) {
  const range =
    item.startedAt && item.endedAt
      ? `${formatRelativeTime(item.endedAt)} · ${item.messageCount}개 메시지`
      : `${item.messageCount}개 메시지`;

  return (
    <footer className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
      <span className="inline-flex items-center gap-1">
        <Users className="h-3 w-3" />
        {item.participants.slice(0, 2).join(", ")}
        {item.participants.length > 2 && ` 외 ${item.participants.length - 2}명`}
      </span>
      <span
        title={
          item.startedAt && item.endedAt
            ? `${formatAbsoluteTime(item.startedAt)} – ${formatAbsoluteTime(item.endedAt)}`
            : undefined
        }
      >
        {range}
      </span>
      <span className="ml-auto inline-flex items-center gap-1 text-amber-700">
        <ShieldOff className="h-3 w-3" />
        비공식
      </span>
    </footer>
  );
}
