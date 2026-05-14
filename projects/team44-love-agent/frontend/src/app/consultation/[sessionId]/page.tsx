'use client';

import { useRouter } from 'next/navigation';
import { useConsultationStore } from '@/stores/consultationStore';
import { AGENTS } from '@/mocks/agents';
import { RootLayout } from '@/components/layout';
import { ChatPhase, FinalAdvicePhase, ResultPhase } from '@/components/consultation';
import { LoadingOverlay, ErrorMessage } from '@/components/status';

export default function ConsultationPage() {
  const router = useRouter();
  const {
    step,
    currentRound,
    session,
    status,
    punchline,
    punchlineLoading,
    goToStep,
    fetchPunchline,
    reset,
  } = useConsultationStore();

  // 새 상담 시작: store 초기화 + 홈으로 이동 (URL이 그대로면 세션 없음 에러가 뜸).
  function handleReset() {
    reset();
    router.push('/');
  }

  if (step === 'loading') {
    return <LoadingOverlay phase={status ?? 'analyzing'} />;
  }

  if (!session) {
    return <ErrorMessage message="세션 정보를 찾을 수 없습니다." />;
  }

  if (step === 'result' && !session.finalResult) {
    return <LoadingOverlay phase={status ?? 'summarizing'} />;
  }

  const isChat = step === 'opinions' || step === 'discussion';
  const isFinalAdvice = step === 'final_advice';
  const canReview = !!session.finalResult;

  async function handleShowFinalAdvice() {
    await fetchPunchline();
    goToStep('final_advice');
  }

  function renderContent() {
    if (!session) return null;

    if (isChat) {
      return (
        <ChatPhase
          userInput={session.userInput}
          agents={AGENTS}
          opinions={session.opinions}
          rounds={session.rounds}
          status={status}
          canReview={canReview}
          onFinalReview={() => goToStep('result')}
        />
      );
    }

    if (isFinalAdvice && punchline) {
      return (
        <FinalAdvicePhase
          agents={AGENTS}
          punchline={punchline}
          onBack={() => goToStep('result')}
          onReset={handleReset}
        />
      );
    }

    if (step === 'result' && session.finalResult) {
      return (
        <ResultPhase
          agents={AGENTS}
          result={session.finalResult}
          onShowFinalAdvice={handleShowFinalAdvice}
          isLoadingFinalAdvice={punchlineLoading}
        />
      );
    }

    return null;
  }

  return (
    <RootLayout
      agents={AGENTS}
      step={step}
      currentRound={currentRound}
      opinions={session.opinions}
      isLastRound={true}
      onNext={() => goToStep('result')}
      showRightPanel={!isChat && !isFinalAdvice}
      showSidebar={!isFinalAdvice}
    >
      {renderContent()}
    </RootLayout>
  );
}
