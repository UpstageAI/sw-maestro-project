'use client';

// ─── MessageBubble ───
// 메시지 1건을 role에 따라 다르게 렌더링한다.
//   user   → 오른쪽, 보라 그라데이션 버블
//   ai     → 왼쪽, 흰색 버블 + 마크다운 파싱
//   system → 가운데, 회색 알림 (오류 메시지 등)
//
// AI 메시지는 react-markdown으로 렌더링하고, **강조**를 보라색 텍스트(.fact-accent)로 바꾼다.
// fixHangulEmphasis: CommonMark 규칙상 닫는 ** 직후 한글이면 strong이 인식 안 되는 버그를 패치.

import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Paperclip } from 'lucide-react';
import type { ChatMessage } from '@/lib/types';

type Props = {
  message: ChatMessage;
};

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
};

// CommonMark 한글 강조 버그 패치:
// "**186,000원**이" 처럼 닫는 ** 직전이 숫자/특수문자이고 직후가 한글이면 strong이 닫히지 않는다.
// 이 경우 ** 뒤에 공백 한 칸을 자동 삽입해 파싱이 정상 동작하도록 한다.
const ASCII_PUNCT = String.raw`[!-/:-@\[-\`{-~]`;
const HANGUL = String.raw`[가-힣]`;
const HANGUL_EMPHASIS_FIX = new RegExp(
  String.raw`(\*\*[^*\n]*?${ASCII_PUNCT})\*\*(${HANGUL})`,
  'g',
);
const fixHangulEmphasis = (text: string): string =>
  text.replace(HANGUL_EMPHASIS_FIX, '$1** $2');

// AI 메시지용 마크다운 커스텀 렌더러:
// **강조** → .fact-accent (보라 그라데이션 텍스트)
// `코드`   → .fact-chip (라벨 스타일)
const aiMarkdownComponents: Components = {
  strong: ({ children }) => <span className="fact-accent">{children}</span>,
  em: ({ children }) => <span className="fact-accent">{children}</span>,
  code: ({ children }) => <span className="fact-chip">{children}</span>,
  a: ({ children, href }) => (
    <a
      href={href}
      className="text-[var(--accent)] underline underline-offset-2 hover:opacity-80"
    >
      {children}
    </a>
  ),
};

export function MessageBubble({ message }: Props) {
  const { role, content, attachment } = message;

  // system: 가운데 정렬 작은 알림 (오류, 안내 메시지)
  if (role === 'system') {
    return (
      <div className="flex justify-center py-1">
        <p className="rounded-full bg-[var(--bg-subtle)] px-3 py-1 text-[11px] text-[var(--ink-500)]">
          {content}
        </p>
      </div>
    );
  }

  // user: 오른쪽 보라 버블. 첨부 파일이 있으면 파일명을 버블 위에 작게 표시.
  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%]">
          {attachment && (
            <div className="mb-1 flex items-center justify-end gap-1 text-[11px] text-[var(--ink-500)]">
              <Paperclip className="h-3 w-3" />
              <span className="truncate">
                {attachment.name} · {formatBytes(attachment.size)}
              </span>
            </div>
          )}
          {content && (
            <div className="rounded-2xl rounded-tr-md bg-gradient-to-br from-[var(--bubble-user-from)] to-[var(--bubble-user-to)] px-4 py-2.5 text-[15px] leading-relaxed text-[var(--bubble-user-text)] shadow-[0_1px_2px_rgba(91,33,182,0.20),0_8px_20px_-6px_rgba(91,33,182,0.40)]">
              <p className="whitespace-pre-wrap">{content}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ai: 왼쪽 흰색 버블 + 마크다운 렌더링
  return (
    <div className="flex justify-start">
      <div className="fact-md max-w-[82%] rounded-2xl rounded-tl-md bg-[var(--bubble-ai-bg)] px-4 py-3 shadow-[0_1px_2px_rgba(14,11,31,0.04),0_8px_24px_-12px_rgba(14,11,31,0.10)] ring-1 ring-[var(--border-soft)]">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={aiMarkdownComponents}>
          {fixHangulEmphasis(content)}
        </ReactMarkdown>
      </div>
    </div>
  );
}
