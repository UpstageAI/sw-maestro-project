// AI 응답 대기 인디케이터. 보더 제거 + 미세 그림자 + 작은 도트.

export function TypingIndicator() {
  return (
    <div
      className="flex justify-start"
      role="status"
      aria-live="polite"
      aria-label="응답 작성 중"
    >
      <div className="rounded-2xl rounded-tl-md bg-[var(--bubble-ai-bg)] px-4 py-3 shadow-[0_1px_2px_rgba(14,11,31,0.04),0_8px_24px_-12px_rgba(14,11,31,0.10)] ring-1 ring-[var(--border-soft)]">
        <div className="flex items-center gap-1.5">
          <span className="dot" />
          <span className="dot dot-2" />
          <span className="dot dot-3" />
        </div>
      </div>
    </div>
  );
}
