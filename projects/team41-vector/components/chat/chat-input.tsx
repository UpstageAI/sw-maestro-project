'use client';

// ─── ChatInput ───
// 화면 하단 고정 입력 영역. 세 가지 요소로 구성:
//   1. 클립 아이콘 버튼 → 숨겨진 file input 클릭 → CSV 파일 선택
//   2. textarea → 텍스트 입력, Enter 전송 / Shift+Enter 줄바꿈, 자동 높이 조절
//   3. 화살표 버튼 → 메시지 전송
//
// 첨부 파일이 있으면 텍스트 없이도 전송 가능.
// AI 응답 대기 중(isTyping)에는 모든 입력이 비활성화된다.

import { useRef, useState, type KeyboardEvent, type ChangeEvent } from 'react';
import { Paperclip, ArrowUp, X } from 'lucide-react';
import { useChatStore } from '@/lib/store/chat-store';

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
};

export function ChatInput() {
  const [text, setText] = useState('');
  const [attachError, setAttachError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const sendMessage = useChatStore((s) => s.sendMessage);
  const attachFile = useChatStore((s) => s.attachFile);
  const attachment = useChatStore((s) => s.attachment);
  const isTyping = useChatStore((s) => s.isTyping);

  // 텍스트 or 첨부 파일이 있어야 전송 가능
  const canSend = !isTyping && (text.trim().length > 0 || attachment !== null);

  const submit = async () => {
    if (!canSend) return;
    const value = text;
    setText('');
    setAttachError(null);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    await sendMessage(value);
    textareaRef.current?.focus(); // 전송 후 포커스 유지
  };

  // Enter = 전송, Shift+Enter = 줄바꿈
  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  // CSV 파일만 허용. 다른 형식이면 3초 후 자동으로 에러 메시지 사라짐.
  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const isCsv = file.type === 'text/csv' || file.name.toLowerCase().endsWith('.csv');
    if (!isCsv) {
      setAttachError('CSV 파일만 첨부할 수 있어요.');
      e.target.value = '';
      window.setTimeout(() => setAttachError(null), 3000);
      return;
    }
    setAttachError(null);
    attachFile(file);
    e.target.value = ''; // 같은 파일 재첨부 가능하도록 초기화
  };

  // textarea 내용에 따라 높이 자동 조절 (최대 160px)
  const handleTextChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="pt-3 pb-5">
      {/* CSV 형식 오류 메시지 */}
      {attachError && (
        <p className="mb-2 px-1 text-[11px] text-rose-600">{attachError}</p>
      )}

      {/* 첨부 파일 미리보기 칩 */}
      {attachment && (
        <div className="mb-2 flex items-center gap-2">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-[var(--bg-subtle)] px-3 py-1 text-[11px] text-[var(--ink-700)] ring-1 ring-[var(--border-soft)]">
            <Paperclip className="h-3 w-3 text-[var(--accent)]" />
            <span className="max-w-[14rem] truncate">{attachment.name}</span>
            <span className="text-[var(--ink-500)]">· {formatBytes(attachment.size)}</span>
            <button
              type="button"
              onClick={() => attachFile(null)}
              aria-label="첨부 제거"
              className="ml-1 rounded-full p-0.5 text-[var(--ink-500)] hover:bg-[var(--ink-300)]/30 hover:text-[var(--ink-900)]"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        </div>
      )}

      {/* 입력 컨테이너 */}
      <div className="flex items-end gap-2 rounded-2xl bg-[var(--bg-panel)] p-2 shadow-[0_1px_2px_rgba(14,11,31,0.04),0_8px_24px_-12px_rgba(14,11,31,0.12)] ring-1 ring-[var(--border-mid)] transition focus-within:ring-[var(--accent)] focus-within:ring-offset-2 focus-within:ring-offset-[var(--bg-canvas)]">
        {/* 파일 첨부 버튼 (숨겨진 input 트리거) */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          aria-label="CSV 파일 첨부"
          disabled={isTyping}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[var(--ink-500)] transition hover:bg-[var(--bg-subtle)] hover:text-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Paperclip className="h-4 w-4" />
        </button>

        {/* 실제로 숨겨진 file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={handleFile}
        />

        {/* 텍스트 입력창 */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKey}
          rows={1}
          placeholder="메시지를 입력하세요"
          disabled={isTyping}
          className="min-h-[2.25rem] flex-1 resize-none bg-transparent px-1 py-1.5 text-[15px] text-[var(--ink-900)] placeholder:text-[var(--ink-500)]/70 focus:outline-none disabled:opacity-60"
        />

        {/* 전송 버튼 */}
        <button
          type="button"
          onClick={submit}
          disabled={!canSend}
          aria-label="전송"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[var(--bubble-user-from)] to-[var(--bubble-user-to)] text-white shadow-[0_2px_6px_-1px_rgba(91,33,182,0.45),0_8px_18px_-4px_rgba(91,33,182,0.35)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-none disabled:bg-[var(--ink-300)] disabled:shadow-none"
        >
          <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
        </button>
      </div>

      <p className="mt-2 px-1 text-[10px] tracking-wide text-[var(--ink-500)]/80">
        Enter 전송 · Shift+Enter 줄바꿈
      </p>
    </div>
  );
}
