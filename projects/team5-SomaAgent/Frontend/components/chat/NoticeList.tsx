"use client";

import {
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Link2,
  Megaphone,
  Paperclip,
  Pin,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMemo } from "react";
import {
  formatAbsoluteTime,
  formatRelativeTime,
} from "@/lib/relativeTime";
import {
  type NoticeAttachment,
  type NoticeAttachmentType,
  type NoticeCard,
  type NoticeCategory,
  formatFileSize,
  sortNotices,
} from "@/lib/types/notice";

const ATTACHMENT_ICON: Record<NoticeAttachmentType, LucideIcon> = {
  pdf: FileText,
  image: ImageIcon,
  doc: FileText,
  link: Link2,
  other: Paperclip,
};

const ATTACHMENT_TONE: Record<NoticeAttachmentType, string> = {
  pdf: "bg-rose-50 text-rose-700",
  image: "bg-blue-50 text-blue-700",
  doc: "bg-slate-100 text-slate-700",
  link: "bg-slate-100 text-slate-700",
  other: "bg-slate-100 text-slate-700",
};

const CATEGORY_TONE: Record<NoticeCategory, string> = {
  운영: "bg-blue-50 text-blue-700",
  평가: "bg-rose-50 text-rose-700",
  워크숍: "bg-violet-50 text-violet-700",
  시스템: "bg-amber-50 text-amber-700",
  기타: "bg-slate-100 text-slate-600",
};

export function NoticeList({ items }: { items: NoticeCard[] }) {
  // items 참조가 바뀔 때만 정렬 비용을 다시 치름 (파생 상태).
  const sorted = useMemo(() => sortNotices(items ?? []), [items]);
  const pinnedCount = useMemo(
    () => sorted.filter((item) => item.pinned).length,
    [sorted],
  );

  if (!items || items.length === 0) return null;

  return (
    <section
      aria-label={`공지 ${sorted.length}건`}
      className="overflow-hidden rounded-xl border border-slate-200 bg-white"
    >
      <header className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
        <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600">
          <Megaphone className="h-3.5 w-3.5 text-slate-400" />
          공지 {sorted.length}건
        </p>
        {pinnedCount > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-medium text-rose-700">
            <Pin className="h-3 w-3" />
            필독 {pinnedCount}건
          </span>
        )}
      </header>

      <ol className="divide-y divide-slate-100">
        {sorted.map((notice) => (
          <li key={notice.id}>
            <NoticeRow notice={notice} />
          </li>
        ))}
      </ol>
    </section>
  );
}

function NoticeRow({ notice }: { notice: NoticeCard }) {
  const isLink = Boolean(notice.url);
  const Title = isLink ? "a" : "span";
  const titleProps = isLink
    ? {
        href: notice.url,
        target: "_blank",
        rel: "noreferrer",
        className:
          "inline-flex items-baseline gap-1 text-sm font-semibold text-slate-900 underline-offset-2 hover:text-blue-700 hover:underline",
      }
    : { className: "text-sm font-semibold text-slate-900" };

  return (
    <article className="space-y-1.5 px-4 py-3">
      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
        {notice.pinned && (
          <span className="inline-flex items-center gap-1 rounded-md bg-rose-100 px-1.5 py-0.5 font-semibold text-rose-700">
            <Pin className="h-3 w-3" />
            필독
          </span>
        )}
        {notice.category && (
          <span
            className={`rounded-md px-1.5 py-0.5 font-medium ${CATEGORY_TONE[notice.category]}`}
          >
            {notice.category}
          </span>
        )}
        <span className="text-slate-500">{notice.author}</span>
        <span className="text-slate-300">·</span>
        <time
          dateTime={notice.createdAt}
          title={formatAbsoluteTime(notice.createdAt)}
          className="text-slate-500"
        >
          {formatRelativeTime(notice.createdAt)}
        </time>
        {notice.unread && (
          <span
            aria-label="미열람"
            title="미열람"
            className="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-blue-500"
          />
        )}
      </div>

      <div className="min-w-0">
        <Title {...titleProps}>
          <span className="break-keep">{notice.title}</span>
          {isLink && (
            <ExternalLink
              className="h-3 w-3 shrink-0 text-slate-400"
              aria-hidden="true"
            />
          )}
        </Title>
      </div>

      {notice.summary && (
        <p className="line-clamp-2 text-xs leading-relaxed text-slate-600">
          {notice.summary}
        </p>
      )}

      {notice.attachments && notice.attachments.length > 0 && (
        <ul className="flex flex-wrap gap-1.5 pt-1">
          {notice.attachments.map((attachment, index) => (
            <li key={attachment.id ?? `${attachment.type}-${index}`}>
              <AttachmentChip attachment={attachment} />
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function AttachmentChip({ attachment }: { attachment: NoticeAttachment }) {
  const Icon = ATTACHMENT_ICON[attachment.type] ?? Paperclip;
  const tone = ATTACHMENT_TONE[attachment.type] ?? ATTACHMENT_TONE.other;
  const sizeLabel = formatFileSize(attachment.sizeBytes);
  const labelText =
    attachment.type === "pdf"
      ? "PDF 첨부"
      : attachment.type === "image"
        ? "이미지 첨부"
        : attachment.type === "link"
          ? "외부 링크"
          : "첨부";

  const content = (
    <>
      <Icon className="h-3 w-3" aria-hidden="true" />
      <span className="max-w-[14rem] truncate">{attachment.name}</span>
      {sizeLabel && (
        <span className="text-[10px] opacity-70">· {sizeLabel}</span>
      )}
    </>
  );

  const baseClass = `inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium transition ${tone}`;

  if (attachment.url) {
    return (
      <a
        href={attachment.url}
        target="_blank"
        rel="noreferrer"
        aria-label={`${labelText}: ${attachment.name}`}
        title={`${labelText} — ${attachment.name}${sizeLabel ? ` (${sizeLabel})` : ""}`}
        className={`${baseClass} hover:brightness-95`}
      >
        {content}
      </a>
    );
  }

  return (
    <span
      aria-label={`${labelText}: ${attachment.name}`}
      title={`${labelText} — ${attachment.name}${sizeLabel ? ` (${sizeLabel})` : ""}`}
      className={baseClass}
    >
      {content}
    </span>
  );
}
