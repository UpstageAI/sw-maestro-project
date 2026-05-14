'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { RotateCcw } from 'lucide-react';
import { Sidebar } from '@/components/layout';
import { StepBar } from '@/components/layout';
import { InputForm, HowItWorks } from '@/components/consultation';
import { useConsultationStore } from '@/stores/consultationStore';
import { AGENTS } from '@/mocks/agents';
import { inputContent } from '@/content';

export default function HomePage() {
  const router = useRouter();
  const { setUserInput, startConsultation, reset, error } = useConsultationStore();
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(input: string) {
    setUserInput(input);
    setIsSubmitting(true);
    try {
      const consultationId = await startConsultation();
      if (consultationId) {
        router.push(`/consultation/${consultationId}`);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar agents={AGENTS} />
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* 상단 헤더 */}
        <div className="flex shrink-0 items-start justify-between px-10 pt-8 pb-2">
          <div>
            <h1 className="text-2xl font-bold">{inputContent.title || '새로운 연애 고민 상담'}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {inputContent.subtitle || '여러 AI 에이전트가 다양한 관점으로 함께 고민해드립니다.'}
            </p>
          </div>
          <Button variant="outline" size="sm" className="shrink-0 gap-1.5" onClick={reset}>
            <RotateCcw className="size-3.5" />
            {inputContent.newButton}
          </Button>
        </div>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-10 py-4">
          {error && (
            <div className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}
          <InputForm onSubmit={handleSubmit} isLoading={isSubmitting} />

          {/* StepBar 카드 */}
          <div className="flex justify-center rounded-2xl border bg-white px-6 py-4 shadow-sm">
            <StepBar step="input" currentRound={1} />
          </div>

          <HowItWorks />
        </div>
      </main>
    </div>
  );
}
