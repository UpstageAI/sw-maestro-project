"use client";

import { Plus, Search, X } from "lucide-react";
import { useAuth } from "@/lib/contexts/AuthContext";
import { MOCK_HISTORY } from "@/lib/mockChat";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function Sidebar({ open, onClose }: Props) {
  const { user } = useAuth();

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="사이드바 닫기"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-sm lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        } lg:flex`}
      >
        <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-4">
          <button
            type="button"
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />새 대화 시작
          </button>
          <button
            type="button"
            onClick={onClose}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 lg:hidden"
            aria-label="사이드바 닫기"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-4 py-3">
          <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
            <Search className="h-3.5 w-3.5" />
            <input
              type="search"
              placeholder="이전 대화 검색"
              className="flex-1 bg-transparent outline-none placeholder:text-slate-400"
            />
          </label>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 pb-4">
          <p className="px-2 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            최근 대화
          </p>
          <ul className="space-y-0.5">
            {MOCK_HISTORY.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="flex w-full items-start justify-between gap-2 rounded-lg px-2 py-2 text-left text-sm text-slate-700 transition hover:bg-slate-100"
                >
                  <span className="truncate">{item.title}</span>
                  <span className="shrink-0 text-[11px] text-slate-400">
                    {item.date}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="border-t border-slate-200 px-4 py-3 text-xs text-slate-500">
          <p className="font-semibold text-slate-700">
            {user ? `${user.userName} (${user.role})` : "로그인 필요"}
          </p>
          <p>{user ? `${user.somaUserId}` : "AI 생활 비서 · 베타"}</p>
        </div>
      </aside>
    </>
  );
}
