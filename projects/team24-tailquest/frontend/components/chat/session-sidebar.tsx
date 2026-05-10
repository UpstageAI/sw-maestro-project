"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  deleteSession,
  listSessions,
  renameSession,
  type SessionSummary,
} from "@/lib/api";
import { clearChatTurns } from "@/lib/chat-state";

const TQ_ACTIVE_SESSION_KEY = "tq:active_session_id";

function relativeTime(epochSec: number): string {
  const diffMs = Date.now() - epochSec * 1000;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "방금 전";
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}시간 전`;
  const d = new Date(epochSec * 1000);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) {
    return `어제 ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  }
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
}

function trackLabel(track: string): string {
  return track === "cs" ? "CS 기초" : "기술 스택";
}

/** Compact "what's this session about" label.
 *
 *  - Domains present  → up to 2 domain labels (curated catalog)
 *  - No domains, keywords present → "사용자 지정 · {keyword}"
 *  - Neither → "사용자 지정"
 *
 *  Sidebar previously rendered an empty span when domains was empty
 *  (custom-keyword sessions), making the row look like just "1분 전".
 */
function scopeLabel(domains: string[], keywords: string[]): string {
  if (domains.length > 0) {
    const head = domains.slice(0, 2).join(" · ");
    return domains.length > 2 ? `${head} +${domains.length - 2}` : head;
  }
  if (keywords.length > 0) {
    return `사용자 지정 · ${keywords[0]}`;
  }
  return "사용자 지정";
}

interface SessionSidebarProps {
  activeSessionId?: string;
}

export function SessionSidebar({ activeSessionId }: SessionSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchSessions = useCallback(async () => {
    const data = await listSessions();
    setSessions(data);
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions, pathname]);

  function handleNewSession() {
    clearChatTurns();
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(TQ_ACTIVE_SESSION_KEY);
    }
    router.push("/onboarding");
  }

  function handleSelectSession(id: string) {
    router.push(`/chat/${id}`);
  }

  function startEdit(s: SessionSummary, e: React.MouseEvent) {
    e.stopPropagation();
    setEditingId(s.id);
    setDraftTitle(s.title);
    queueMicrotask(() => inputRef.current?.select());
  }

  async function handleDeleteSession(s: SessionSummary, e: React.MouseEvent) {
    e.stopPropagation();
    const ok =
      typeof window !== "undefined" &&
      window.confirm(`'${s.title}' 세션을 삭제할까요? 되돌릴 수 없습니다.`);
    if (!ok) return;
    // Optimistic remove from list.
    setSessions((prev) => prev.filter((x) => x.id !== s.id));
    try {
      await deleteSession(s.id);
    } catch {
      // Reload on failure so the list reflects truth.
      fetchSessions();
      return;
    }
    // If the deleted session was the active one, drop the active key and
    // route to the fresh-session start so the user isn't stuck on a 404 URL.
    if (typeof window !== "undefined") {
      const cached = window.sessionStorage.getItem(TQ_ACTIVE_SESSION_KEY);
      if (cached === s.id) window.sessionStorage.removeItem(TQ_ACTIVE_SESSION_KEY);
    }
    if (s.id === activeSessionId) {
      clearChatTurns();
      router.push("/onboarding");
    }
  }

  async function commitEdit(sessionId: string) {
    const next = draftTitle.trim();
    setEditingId(null);
    const original = sessions.find((s) => s.id === sessionId)?.title ?? "";
    if (!next || next === original) return;
    // Optimistic update
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, title: next } : s)),
    );
    try {
      await renameSession(sessionId, next);
    } catch {
      // Revert on failure
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title: original } : s)),
      );
    }
  }

  return (
    <aside className="hidden lg:flex flex-col h-full w-full bg-canvas border-r border-hairline overflow-hidden">
      {/* Header */}
      <div className="px-md py-sm shrink-0 border-b border-hairline">
        <button
          type="button"
          onClick={handleNewSession}
          className="w-full flex items-center justify-center gap-sm rounded-md border border-dashed border-hairline py-sm text-body-sm text-muted hover:border-ink hover:text-ink transition-colors"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
            add
          </span>
          새 세션
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 min-h-0 overflow-y-auto py-xs" style={{ scrollbarGutter: "stable" }}>
        {sessions.length === 0 ? (
          <div className="mx-md mt-lg rounded-md border border-dashed border-hairline px-md py-lg text-center">
            <p className="text-caption-sm text-muted">아직 면접 기록이 없습니다.</p>
          </div>
        ) : (
          <ul className="flex flex-col gap-xxs px-xs">
            {sessions.map((s) => {
              const isActive = s.id === activeSessionId;
              const isEditing = editingId === s.id;
              return (
                <li key={s.id}>
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => !isEditing && handleSelectSession(s.id)}
                    onKeyDown={(e) => {
                      if (!isEditing && (e.key === "Enter" || e.key === " ")) {
                        e.preventDefault();
                        handleSelectSession(s.id);
                      }
                    }}
                    className={[
                      "group w-full text-left rounded-md px-md py-sm transition-colors cursor-pointer",
                      isActive
                        ? "bg-surface-strong border-l-2 border-l-rausch"
                        : "hover:bg-surface-soft border-l-2 border-l-transparent",
                    ].join(" ")}
                  >
                    {/* Track pill + title (or inline editor) */}
                    <div className="flex items-center gap-xs mb-xxs">
                      <span className="pill bg-surface-strong text-ink text-uppercase-tag shrink-0">
                        {trackLabel(s.track)}
                      </span>
                      {isEditing ? (
                        <input
                          ref={inputRef}
                          type="text"
                          value={draftTitle}
                          maxLength={80}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => setDraftTitle(e.target.value)}
                          onBlur={() => commitEdit(s.id)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              commitEdit(s.id);
                            } else if (e.key === "Escape") {
                              e.preventDefault();
                              setEditingId(null);
                            }
                          }}
                          autoFocus
                          className="flex-1 min-w-0 bg-canvas border border-hairline rounded-sm px-xs py-0 text-body-sm text-ink focus:outline-none focus:border-ink"
                        />
                      ) : (
                        <>
                          <span className="text-body-sm text-ink font-medium truncate flex-1 min-w-0">
                            {s.title}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => startEdit(s, e)}
                            aria-label="이름 변경"
                            className="opacity-0 group-hover:opacity-100 text-muted hover:text-ink transition-opacity shrink-0"
                          >
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                              edit
                            </span>
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleDeleteSession(s, e)}
                            aria-label="세션 삭제"
                            title="세션 삭제"
                            className="opacity-0 group-hover:opacity-100 text-muted hover:text-rausch transition-opacity shrink-0"
                          >
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                              delete
                            </span>
                          </button>
                        </>
                      )}
                    </div>

                    {/* Scope label + relative time */}
                    <div className="flex items-center gap-xs min-w-0">
                      <span className="text-caption-sm text-muted truncate">
                        {scopeLabel(s.domains, s.keywords)}
                      </span>
                      <span className="text-caption-sm text-muted shrink-0">
                        · {relativeTime(s.updatedAt)}
                      </span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
