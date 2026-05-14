"use client";

import { LogOut, Menu } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { SyncStatusBadge } from "@/components/sync/SyncStatusBadge";
import { useAuth } from "@/lib/contexts/AuthContext";

/** 임시 OFF: 헤더에서 동기화 배지 미표시(컴포넌트·훅은 유지). 다시 켤 때 true로 변경 */
const SHOW_SYNC_STATUS_BADGE = false;

type Props = {
  onToggleSidebar: () => void;
};

function initialOf(name: string | undefined): string {
  if (!name) return "?";
  const trimmed = name.trim();
  if (!trimmed) return "?";
  return trimmed.slice(0, 1);
}

export function ChatHeader({ onToggleSidebar }: Props) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logout();
      router.replace("/login");
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="grid h-9 w-9 place-items-center rounded-lg text-slate-600 transition hover:bg-slate-100 lg:hidden"
          aria-label="사이드바 열기"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div>
          <p className="text-base font-semibold tracking-tight text-slate-900">
            SomaAgent
          </p>
          <p className="text-[11px] text-slate-500">AI 생활 비서</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {SHOW_SYNC_STATUS_BADGE ? <SyncStatusBadge /> : null}

        {user && (
          <div className="hidden text-right text-xs leading-tight sm:block">
            <p className="font-semibold text-slate-700">{user.userName}</p>
            <p className="text-slate-400">{user.somaUserId}</p>
          </div>
        )}

        <button
          type="button"
          className="grid h-9 w-9 place-items-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700"
          aria-label={user ? `${user.userName} 프로필` : "내 프로필"}
        >
          {initialOf(user?.userName)}
        </button>

        <button
          type="button"
          onClick={handleLogout}
          disabled={loggingOut}
          className="grid h-9 w-9 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label="로그아웃"
          title="로그아웃"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
