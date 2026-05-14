"use client";

interface UserMenuProps {
  email: string;
  onLogout: () => void;
}

export function UserMenu({ email, onLogout }: UserMenuProps) {
  return (
    <div className="flex items-center gap-sm">
      <span className="text-sm text-graphite hidden sm:block">{email}</span>
      <button
        onClick={onLogout}
        className="text-sm font-medium text-ink border border-hairline rounded-md px-3 py-1.5 bg-canvas hover:bg-paper transition-colors"
      >
        로그아웃
      </button>
    </div>
  );
}
