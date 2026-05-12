// 미니멀 헤더 — 보라 그라데이션 로고(팩폭머니) + 미세 도트 마크.

export function Header() {
  return (
    <header className="flex items-center border-b border-[var(--border-soft)] py-4">
      <div className="flex items-center gap-3">
        <span className="brand-mark text-lg sm:text-xl">팩폭머니</span>
        <span className="hidden self-end pb-1 text-[11px] tracking-wider text-[var(--ink-500)] uppercase sm:inline">
          Fact · Money Coach
        </span>
      </div>
    </header>
  );
}
