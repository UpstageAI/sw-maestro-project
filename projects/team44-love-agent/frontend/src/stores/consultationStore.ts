import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  ConsultationHistoryEntry,
  ConsultationSession,
  ConsultationStep,
  DiscussionRound,
  Punchline,
} from '@/types';
import {
  ApiError,
  requestPunchline,
  startConsultation as apiStartConsultation,
  subscribeEvents,
  toDiscussionMessage,
  toOpinion,
  toSession,
  type BackendConsultationResponse,
} from '@/lib/api';

const EMPTY_SESSION: ConsultationSession = {
  userInput: '',
  opinions: [],
  rounds: [],
  finalResult: null,
};

const HISTORY_LIMIT = 50;

type TransientState = Pick<
  ConsultationState,
  | 'step'
  | 'currentRound'
  | 'session'
  | 'consultationId'
  | 'error'
  | 'status'
  | 'punchline'
  | 'punchlineLoading'
>;

const INITIAL_TRANSIENT: TransientState = {
  step: 'input',
  currentRound: 1,
  session: null,
  consultationId: null,
  error: null,
  status: null,
  punchline: null,
  punchlineLoading: false,
};

// SSE cleanup 함수는 비직렬화 자료라 store 바깥 모듈 스코프에서 관리.
let activeSseCleanup: (() => void) | null = null;

interface ConsultationState {
  step: ConsultationStep;
  currentRound: number;
  session: ConsultationSession | null;
  consultationId: string | null;
  error: string | null;
  status: BackendConsultationResponse['status'] | null;
  punchline: Punchline | null;
  punchlineLoading: boolean;

  // 영속화되는 상담 기록 (localStorage). 시작 시점 기준 최신 순.
  history: ConsultationHistoryEntry[];

  setUserInput: (input: string) => void;
  startConsultation: () => Promise<string | null>;
  setSession: (session: ConsultationSession) => void;
  goToNextRound: () => void;
  goToStep: (step: ConsultationStep, round?: number) => void;
  reset: () => void;
  fetchPunchline: () => Promise<void>;
  loadFromHistory: (consultationId: string) => boolean;
  clearHistory: () => void;
  removeFromHistory: (consultationId: string) => void;
}

// 내부: 현재 store 상태로부터 history 엔트리 만들기.
function upsertHistory(
  history: ConsultationHistoryEntry[],
  entry: ConsultationHistoryEntry,
): ConsultationHistoryEntry[] {
  const without = history.filter((e) => e.consultationId !== entry.consultationId);
  return [entry, ...without].slice(0, HISTORY_LIMIT);
}

export const useConsultationStore = create<ConsultationState>()(
  persist(
    (set, get) => ({
      ...INITIAL_TRANSIENT,
      history: [],

      setUserInput: (input) => {
        set((state) => ({
          session: {
            ...(state.session ?? EMPTY_SESSION),
            userInput: input,
          },
        }));
      },

      startConsultation: async () => {
        const userInput = get().session?.userInput ?? '';

        if (process.env.NEXT_PUBLIC_USE_MOCK === 'true') {
          const { MOCK_CONSULTATION } = await import('@/mocks/consultation');
          set({
            step: 'opinions',
            session: MOCK_CONSULTATION,
            currentRound: 1,
            consultationId: 'mock',
            error: null,
            status: 'completed',
          });
          return 'mock';
        }

        // 이전 상담의 SSE가 살아있으면 정리.
        activeSseCleanup?.();
        activeSseCleanup = null;

        set({
          step: 'loading',
          error: null,
          session: { ...EMPTY_SESSION, userInput },
          status: 'pending',
          punchline: null,
          punchlineLoading: false,
        });

        let consultationId: string;
        try {
          consultationId = await apiStartConsultation(userInput);
        } catch (err) {
          const message =
            err instanceof ApiError
              ? `백엔드 통신 실패 (${err.status}): ${err.message}`
              : err instanceof Error
                ? err.message
                : '알 수 없는 오류가 발생했습니다.';
          set({ step: 'input', error: message, status: null });
          return null;
        }

        const startedAt = new Date().toISOString();
        set({ consultationId });

        activeSseCleanup = subscribeEvents(consultationId, {
          onStatusChanged: (status) => {
            if (get().consultationId !== consultationId) return;
            set({ status });
          },

          onAgentMessage: (round, message) => {
            if (get().consultationId !== consultationId) return;

            if (round === 'round_1') {
              const opinion = toOpinion(message);
              set((s) => {
                const baseSession = s.session ?? EMPTY_SESSION;
                const exists = baseSession.opinions.some((o) => o.agentId === opinion.agentId);
                const opinions = exists
                  ? baseSession.opinions
                  : [...baseSession.opinions, opinion];
                const session = { ...baseSession, opinions };
                const nextStep = s.step === 'loading' ? 'opinions' : s.step;
                return { session, step: nextStep };
              });
              return;
            }

            const targetRoundNumber = round === 'round_2' ? 1 : 2;
            const label = round === 'round_2' ? 'rebuttal' : 'deepdive';
            const msg = toDiscussionMessage(message, label);

            set((s) => {
              const baseSession = s.session ?? EMPTY_SESSION;
              const existing = baseSession.rounds.find(
                (r) => r.roundNumber === targetRoundNumber,
              );
              let rounds: DiscussionRound[];
              if (existing) {
                const alreadyHas = existing.messages.some((m) => m.agentId === msg.agentId);
                const newMessages = alreadyHas
                  ? existing.messages
                  : [...existing.messages, msg];
                rounds = baseSession.rounds.map((r) =>
                  r.roundNumber === targetRoundNumber ? { ...r, messages: newMessages } : r,
                );
              } else {
                rounds = [
                  ...baseSession.rounds,
                  { roundNumber: targetRoundNumber, messages: [msg] },
                ];
                rounds.sort((a, b) => a.roundNumber - b.roundNumber);
              }

              let nextStep: typeof s.step = s.step;
              let nextCurrentRound = s.currentRound;
              if (s.step !== 'result') {
                if (s.step === 'loading' || s.step === 'opinions') {
                  nextStep = 'discussion';
                  nextCurrentRound = targetRoundNumber;
                } else if (s.step === 'discussion' && s.currentRound < targetRoundNumber) {
                  nextCurrentRound = targetRoundNumber;
                }
              }

              return {
                session: { ...baseSession, rounds },
                step: nextStep,
                currentRound: nextCurrentRound,
              };
            });
          },

          onCompleted: (response) => {
            if (get().consultationId !== consultationId) return;
            const finalSession = toSession(response);
            set((s) => {
              // 완료된 상담을 history에 push (영속).
              const entry: ConsultationHistoryEntry = {
                consultationId,
                userInput: response.user_question || finalSession.userInput,
                startedAt: response.started_at || startedAt,
                completedAt: response.completed_at ?? null,
                status: response.status,
                session: finalSession,
                punchline: s.punchline,
              };
              return {
                session: finalSession,
                step: s.step === 'loading' ? 'opinions' : s.step,
                status: response.status,
                history: upsertHistory(s.history, entry),
              };
            });
          },

          onError: (err) => {
            if (get().consultationId !== consultationId) return;
            const message =
              'user_message_key' in err
                ? `상담이 중단되었습니다 (${err.user_message_key}).`
                : err.message || '상담 실행 중 오류가 발생했습니다.';
            set({ step: 'input', error: message, status: 'failed' });
          },

          onClose: () => {
            if (get().consultationId === consultationId) {
              activeSseCleanup = null;
            }
          },
        });

        return consultationId;
      },

      setSession: (session) => {
        set({ session, step: 'opinions' });
      },

      goToNextRound: () => {
        const { step, session, currentRound } = get();
        if (!session) return;

        if (step === 'opinions') {
          if (session.rounds.length > 0) {
            set({ step: 'discussion', currentRound: 1 });
          } else {
            set({ step: 'result' });
          }
        } else if (step === 'discussion') {
          if (currentRound < session.rounds.length) {
            set({ currentRound: currentRound + 1 });
          } else {
            set({ step: 'result' });
          }
        }
      },

      goToStep: (step, round) => {
        set({ step, ...(round !== undefined ? { currentRound: round } : {}) });
      },

      reset: () => {
        activeSseCleanup?.();
        activeSseCleanup = null;
        set(INITIAL_TRANSIENT);
      },

      fetchPunchline: async () => {
        const { consultationId, punchline, punchlineLoading } = get();
        if (!consultationId || punchline || punchlineLoading) return;
        set({ punchlineLoading: true });
        try {
          const res = await requestPunchline(consultationId);
          const newPunchline: Punchline = {
            chosenAgentId: res.chosen_agent_id,
            oneLiner: res.one_liner,
            vibe: res.vibe,
            rationale: res.rationale,
          };
          set((s) => {
            // 진행 중 또는 직전 완료된 history 엔트리가 있으면 punchline 업데이트.
            const updatedHistory = s.history.map((e) =>
              e.consultationId === consultationId ? { ...e, punchline: newPunchline } : e,
            );
            return {
              punchline: newPunchline,
              punchlineLoading: false,
              history: updatedHistory,
            };
          });
        } catch (err) {
          const message =
            err instanceof ApiError
              ? `최종 조언 요청 실패 (${err.status}): ${err.message}`
              : err instanceof Error
                ? err.message
                : '최종 조언을 받지 못했습니다.';
          set({ punchlineLoading: false, error: message });
        }
      },

      loadFromHistory: (consultationId) => {
        const entry = get().history.find((e) => e.consultationId === consultationId);
        if (!entry) return false;
        // SSE 연결 정리 (다른 상담이 진행 중이었다면).
        activeSseCleanup?.();
        activeSseCleanup = null;
        set({
          consultationId: entry.consultationId,
          session: entry.session,
          status: (entry.status as BackendConsultationResponse['status']) ?? 'completed',
          punchline: entry.punchline,
          punchlineLoading: false,
          // 결과 화면으로 바로 표시.
          step: entry.session.finalResult ? 'result' : 'opinions',
          currentRound: 1,
          error: null,
        });
        return true;
      },

      clearHistory: () => {
        set({ history: [] });
      },

      removeFromHistory: (consultationId) => {
        set((s) => ({
          history: s.history.filter((e) => e.consultationId !== consultationId),
        }));
      },
    }),
    {
      name: 'ai-consult-history',
      storage: createJSONStorage(() => localStorage),
      // history만 영속 — 진행 중 세션이나 SSE 상태는 새 페이지 로드 때 다시 초기화.
      partialize: (s) => ({ history: s.history }),
      version: 1,
    },
  ),
);
