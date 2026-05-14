'use client';

import { Sidebar } from '@/components/layout';
import { AgentAvatar } from '@/components/agents';
import { AGENTS } from '@/mocks/agents';

export default function AgentsPage() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar agents={AGENTS} />
      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="shrink-0 px-10 pb-2 pt-8">
          <h1 className="text-2xl font-bold">에이전트 소개</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            상담에 참여하는 4명의 에이전트가 어떤 관점·말투로 조언하는지 확인합니다.
          </p>
        </header>

        <div className="flex-1 overflow-y-auto px-10 py-4">
          <section className="grid gap-4 md:grid-cols-2">
            {AGENTS.map((agent) => (
              <article
                key={agent.id}
                className="overflow-hidden rounded-2xl border bg-white shadow-sm"
              >
                <div className="flex items-center gap-4 p-5">
                  <div
                    className="relative shrink-0 overflow-hidden rounded-2xl"
                    style={{
                      width: 96,
                      height: 96,
                      outline: `3px solid color-mix(in oklch, var(--${agent.colorKey}) 50%, white)`,
                    }}
                  >
                    <img
                      src={agent.image}
                      alt={agent.name}
                      className="size-full object-cover"
                      draggable={false}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-lg font-bold leading-tight">{agent.name}</h2>
                    <p className="mt-1 text-sm text-muted-foreground">{agent.persona}</p>
                  </div>
                </div>
                <div
                  className="border-t px-5 py-3 text-xs leading-relaxed"
                  style={{
                    backgroundColor: `color-mix(in oklch, var(--${agent.colorKey}) 8%, white)`,
                  }}
                >
                  <span className="font-semibold text-foreground">말투 · 톤</span>
                  <p className="mt-1 text-muted-foreground">{agent.tone}</p>
                </div>
              </article>
            ))}
          </section>
        </div>
      </main>
    </div>
  );
}
