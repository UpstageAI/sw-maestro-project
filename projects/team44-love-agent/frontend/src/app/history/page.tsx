'use client';

import { useRouter } from 'next/navigation';
import { Clock3, History, MessageSquareText, RotateCcw, Trash2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sidebar } from '@/components/layout';
import { useConsultationStore } from '@/stores/consultationStore';
import { AGENTS } from '@/mocks/agents';
import type { ConsultationHistoryEntry } from '@/types';

export default function HistoryPage() {
  const router = useRouter();
  const {
    history,
    consultationId: currentId,
    reset,
    loadFromHistory,
    removeFromHistory,
    clearHistory,
  } = useConsultationStore();

  function handleNewConsultation() {
    reset();
    router.push('/');
  }

  function handleOpenEntry(entry: ConsultationHistoryEntry) {
    const ok = loadFromHistory(entry.consultationId);
    if (ok) {
      router.push(`/consultation/${entry.consultationId}`);
    }
  }

  function handleRemove(e: React.MouseEvent, consultationId: string) {
    e.stopPropagation();
    if (confirm('이 상담 기록을 삭제할까요?')) {
      removeFromHistory(consultationId);
    }
  }

  function handleClearAll() {
    if (history.length === 0) return;
    if (confirm(`상담 기록 ${history.length}개를 모두 지울까요?`)) {
      clearHistory();
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar agents={AGENTS} />
      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="flex shrink-0 items-start justify-between gap-3 px-10 pb-2 pt-8">
          <div>
            <h1 className="text-2xl font-bold">상담 기록</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              브라우저에 저장된 지난 상담 목록 ({history.length}개) — 클릭해서 다시 열어볼 수 있어요.
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            {history.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleClearAll}
              >
                <Trash2 className="size-3.5" />
                전체 삭제
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={handleNewConsultation}
            >
              <RotateCcw className="size-3.5" />
              새 상담 시작
            </Button>
          </div>
        </header>

        <div className="flex flex-1 overflow-y-auto px-10 py-4">
          {history.length === 0 ? (
            <section className="flex w-full flex-col items-center justify-center rounded-2xl border bg-white p-8 text-center shadow-sm">
              <History className="size-10 text-muted-foreground" />
              <h2 className="mt-4 text-lg font-semibold">아직 상담 기록이 없어요</h2>
              <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
                상담을 완료하면 이 화면에 자동으로 쌓입니다. 기록은 브라우저(localStorage)에 저장되며, 백엔드가
                꺼져도 결과를 다시 열어볼 수 있어요.
              </p>
              <Button className="mt-5" onClick={handleNewConsultation}>
                상담 시작하기
              </Button>
            </section>
          ) : (
            <ul className="flex w-full list-none flex-col gap-2 p-0">
              {history.map((entry) => {
                const isCurrent = entry.consultationId === currentId;
                const completed = entry.session.finalResult !== null;
                return (
                  <li key={entry.consultationId} className="list-none">
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => handleOpenEntry(entry)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          handleOpenEntry(entry);
                        }
                      }}
                      className="group relative flex w-full cursor-pointer flex-col gap-2 rounded-2xl border bg-white p-5 text-left shadow-sm transition-all hover:border-primary/50 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    >
                      {/* 삭제 버튼 */}
                      <button
                        type="button"
                        onClick={(e) => handleRemove(e, entry.consultationId)}
                        className="absolute right-3 top-3 cursor-pointer rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                        aria-label="이 상담 기록 삭제"
                      >
                        <X className="size-4" />
                      </button>

                      {/* 헤더 */}
                      <div className="flex flex-wrap items-center gap-2 pr-8">
                        <StatusBadge status={entry.status} completed={completed} />
                        {isCurrent && (
                          <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                            현재 세션
                          </span>
                        )}
                        <span className="text-xs text-muted-foreground">
                          {formatDate(entry.startedAt)}
                        </span>
                      </div>

                      {/* 질문 */}
                      <p className="line-clamp-2 text-base font-medium text-foreground">
                        {entry.userInput}
                      </p>

                      {/* punchline 미리보기 */}
                      {entry.punchline && (
                        <p className="text-sm font-semibold text-primary">
                          🎯 {entry.punchline.oneLiner}
                        </p>
                      )}

                      {/* 메타 */}
                      <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <MessageSquareText className="size-3.5" />
                          의견 {entry.session.opinions.length}개 · 토론{' '}
                          {entry.session.rounds.reduce((s, r) => s + r.messages.length, 0)}개
                        </span>
                        {entry.completedAt && (
                          <span className="flex items-center gap-1">
                            <Clock3 className="size-3.5" />
                            {durationLabel(entry.startedAt, entry.completedAt)}
                          </span>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}

function StatusBadge({ status, completed }: { status: string; completed: boolean }) {
  if (status === 'completed') {
    return <Badge color="green">완료</Badge>;
  }
  if (status === 'terminated') {
    return <Badge color="amber">조기 종료</Badge>;
  }
  if (status === 'failed') {
    return <Badge color="red">실패</Badge>;
  }
  if (completed) {
    return <Badge color="green">완료</Badge>;
  }
  return <Badge color="gray">진행 중</Badge>;
}

function Badge({ color, children }: { color: 'green' | 'amber' | 'red' | 'gray'; children: React.ReactNode }) {
  const palette = {
    green: 'bg-emerald-100 text-emerald-700',
    amber: 'bg-amber-100 text-amber-700',
    red: 'bg-rose-100 text-rose-700',
    gray: 'bg-muted text-muted-foreground',
  } as const;
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${palette[color]}`}>{children}</span>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function durationLabel(startIso: string, endIso: string): string {
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  if (isNaN(start) || isNaN(end)) return '';
  const secs = Math.max(0, Math.round((end - start) / 1000));
  if (secs < 60) return `${secs}초`;
  const mins = Math.floor(secs / 60);
  const remSec = secs % 60;
  return remSec ? `${mins}분 ${remSec}초` : `${mins}분`;
}
