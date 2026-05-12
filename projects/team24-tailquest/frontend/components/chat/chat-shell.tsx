"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Icon } from "@/components/chrome/icon";
import { AnalysisRail } from "@/components/chat/analysis-rail";
import { Composer } from "@/components/chat/composer";
import { ConversationTurn } from "@/components/chat/conversation-turn";
import { SessionSidebar } from "@/components/chat/session-sidebar";

import {
  generateSeedQuestion,
  getSession,
  listMaterials,
  listSessions,
  submitInterview,
  submitInterviewStream,
  type MaterialResponse,
  type StreamDone,
} from "@/lib/api";
import {
  clearChatTurns,
  loadChatTurns,
  newTurnId,
  saveChatTurns,
  type Turn,
} from "@/lib/chat-state";
import { findDomain, type Domain } from "@/lib/domains";
import {
  getSelectedMaterialIds,
  reconcileSelectedMaterials,
} from "@/lib/materials-selection";
import { loadOnboarding, type OnboardingState } from "@/lib/onboarding-state";

const TQ_ACTIVE_SESSION_KEY = "tq:active_session_id";

const MAX_PROBE_DEPTH = 3;

function consecutiveFollowUpsOnDomain(
  turns: Turn[],
  domainLabel: string | undefined,
): number {
  if (!domainLabel) return 0;
  let count = 0;
  for (let i = turns.length - 1; i >= 0; i--) {
    const t = turns[i];
    if (t.source !== "follow-up") break;
    if (t.domainLabel !== domainLabel) break;
    count++;
  }
  return count;
}

function getActiveSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TQ_ACTIVE_SESSION_KEY);
}

function setActiveSessionId(id: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(TQ_ACTIVE_SESSION_KEY, id);
}

interface ChatShellProps {
  /** Session id from /chat/[sessionId] route. When provided, hydrate from BE. */
  sessionId?: string;
}

export function ChatShell({ sessionId: propSessionId }: ChatShellProps) {
  const router = useRouter();
  const [onboarding, setOnboarding] = useState<OnboardingState | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  // Stage label surfaced under the loading indicator while /sessions/stream
  // walks through analyzer → retriever → generator → evaluator. Cleared in
  // the finally block of handleSubmit.
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(true);
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Track the DB session ID and the pre-allocated next turn ID.
  const [dbSessionId, setDbSessionId] = useState<string | null>(null);
  const [nextTurnId, setNextTurnId] = useState<string | null>(null);
  // All uploaded materials (for resolving session materialIds → names).
  const [allMaterials, setAllMaterials] = useState<MaterialResponse[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  // Tracks which session keys have already had a seed fired, so:
  //   1. Strict-mode dev double-mount can't double-create sessions
  //   2. Switching from /chat/A → /chat/B → back to /chat/A doesn't re-seed A
  // Key is propSessionId for existing sessions, "__new__" for the brand-new flow.
  const seededSessionsRef = useRef<Set<string>>(new Set());

  const selectedDomains: Domain[] = useMemo(() => {
    if (!onboarding) return [];
    return onboarding.domainIds
      .map(findDomain)
      .filter((d): d is Domain => d !== undefined);
  }, [onboarding]);

  const customKeywords = onboarding?.customKeywords ?? [];

  const materialIds: string[] = useMemo(() => {
    const stored = getSelectedMaterialIds();
    if (stored.length > 0) return stored;
    return onboarding?.materialIds ?? [];
  }, [onboarding]);

  // Resolve material IDs → MaterialResponse for the right rail's
  // "이 세션의 자료" card. allMaterials is fetched once on mount below.
  const sessionMaterials = useMemo(() => {
    if (materialIds.length === 0 || allMaterials.length === 0) return [];
    const idSet = new Set(materialIds);
    return allMaterials.filter((m) => idSet.has(m.id));
  }, [materialIds, allMaterials]);

  // Fetch the global material list once so we can resolve names. Failures
  // are silent — the rail just hides the card.
  useEffect(() => {
    listMaterials()
      .then(setAllMaterials)
      .catch(() => setAllMaterials([]));
  }, []);

  // Hydrate / seed effect.
  //
  // Re-runs on `propSessionId` change (sidebar nav between sessions). Each run
  // owns its own AbortController; the cleanup aborts any in-flight fetches so
  // their late `setTurns(...)` commits are dropped — that prevents the bug
  // where leaving session A and coming back made A's turn list balloon with
  // ghost questions from B's auto-seed call resolving into A's state.
  useEffect(() => {
    const ctrl = new AbortController();
    const sessionKey = propSessionId ?? "__new__";

    if (propSessionId) {
      // Existing-session path. Reset visible state so the user sees a clean
      // skeleton instead of the previous session's turns flashing through.
      setSeeding(true);
      setTurns([]);
      setError(null);
      setSelectedTurnId(null);
      setNextTurnId(null);

      (async () => {
        try {
          const detail = await getSession(propSessionId);
          if (ctrl.signal.aborted) return;

          const hydratedTurns: Turn[] = detail.turns.map((td) => ({
            id: td.id,
            level: (td.level as Turn["level"]) ?? "seed",
            source: (td.source.replace("_", "-") as Turn["source"]) ?? "seed",
            domainLabel: td.domainLabel,
            question: td.question,
            rationale: td.rationale,
            answer: td.answer ?? undefined,
            notes: td.notes,
            followUps: td.followUps,
            answerQuality: td.answerQuality as Turn["answerQuality"],
            explanation: td.explanation || undefined,
            questionIntent: td.questionIntent || undefined,
            score: td.score ?? undefined,
            retrievedContext: td.retrievedContext,
            citations: td.citations,
            threadId: td.threadId ?? undefined,
            createdAt: td.createdAt,
          }));
          setTurns(hydratedTurns);
          setDbSessionId(propSessionId);
          setActiveSessionId(propSessionId);

          const hydratedOnboarding: OnboardingState = {
            track: detail.track as "cs" | "stack",
            domainIds: [],
            customKeywords: [...detail.domains, ...detail.keywords],
            materials: [],
            materialIds: detail.materialIds,
          };
          setOnboarding(hydratedOnboarding);

          if (hydratedTurns.length > 0) {
            setSelectedTurnId(hydratedTurns[hydratedTurns.length - 1].id);
          }

          const last = hydratedTurns.at(-1);
          if (last && last.answer !== undefined) {
            // Last turn already answered — auto-seed the next question, but
            // only once per session key (prevents Strict-Mode double-fire and
            // re-fire when user navigates back to this session).
            if (seededSessionsRef.current.has(sessionKey)) return;
            seededSessionsRef.current.add(sessionKey);
            try {
              const askedSoFar = Array.from(
                new Set(hydratedTurns.map((t) => t.question).filter(Boolean)),
              );
              const seed = await generateSeedQuestion({
                track: hydratedOnboarding.track,
                domains: detail.domains,
                keywords: detail.keywords,
                exclude_questions: askedSoFar,
                material_ids: detail.materialIds,
                sessionId: propSessionId,
              });
              if (ctrl.signal.aborted) return;
              if (seed.turnId) setNextTurnId(seed.turnId);
              setTurns((prev) => [
                ...prev,
                {
                  id: seed.turnId ?? newTurnId(),
                  level: "seed",
                  source: "seed",
                  question: seed.question,
                  rationale: `${seed.domain_label} 분야의 다음 질문`,
                  domainLabel: seed.domain_label,
                  citations: seed.citations,
                  createdAt: Date.now(),
                },
              ]);
            } catch {
              // Seed failed — user can still review prior turns; non-fatal.
            }
          } else if (last) {
            // Last turn is unanswered — that's the active turn.
            setNextTurnId(last.id);
          }
        } catch (e) {
          if (ctrl.signal.aborted) return;
          setError(
            e instanceof Error
              ? `세션을 불러오지 못했습니다: ${e.message}`
              : "세션을 불러오지 못했습니다.",
          );
        } finally {
          if (!ctrl.signal.aborted) setSeeding(false);
        }
      })();

      return () => ctrl.abort();
    }

    // Brand-new-session path (URL is /chat with no sessionId).
    //
    // If the user lands here without an in-progress onboarding draft, they
    // either (a) just logged in and have prior chat history → resume the most
    // recent session, or (b) really are starting fresh → go to onboarding.
    // We can't tell from sessionStorage alone, so ask the BE.
    const state = loadOnboarding();
    if (
      !state ||
      (state.domainIds.length === 0 && (state.customKeywords ?? []).length === 0)
    ) {
      (async () => {
        try {
          const sessions = await listSessions();
          if (ctrl.signal.aborted) return;
          if (sessions.length > 0) {
            router.replace(`/chat/${sessions[0].id}`);
          } else {
            router.replace("/onboarding");
          }
        } catch {
          if (!ctrl.signal.aborted) router.replace("/onboarding");
        }
      })();
      return () => ctrl.abort();
    }
    setOnboarding(state);

    const persisted = loadChatTurns();
    if (persisted.length > 0) {
      setTurns(persisted);
      setSeeding(false);
      const sid = getActiveSessionId();
      if (sid) setDbSessionId(sid);
      return () => ctrl.abort();
    }

    if (seededSessionsRef.current.has(sessionKey)) {
      return () => ctrl.abort();
    }
    seededSessionsRef.current.add(sessionKey);

    (async () => {
      const labels = state.domainIds
        .map(findDomain)
        .filter((d): d is Domain => d !== undefined)
        .map((d) => d.label);

      let mountMaterialIds: string[] = [];
      try {
        mountMaterialIds = await reconcileSelectedMaterials();
      } catch {
        mountMaterialIds = getSelectedMaterialIds();
      }
      if (mountMaterialIds.length === 0) {
        mountMaterialIds = state.materialIds ?? [];
      }

      try {
        const seed = await generateSeedQuestion({
          track: state.track,
          domains: labels,
          keywords: state.customKeywords ?? [],
          exclude_questions: [],
          material_ids: mountMaterialIds,
        });
        if (ctrl.signal.aborted) return;

        if (seed.sessionId) {
          setDbSessionId(seed.sessionId);
          setActiveSessionId(seed.sessionId);
          if (window.location.pathname === "/chat") {
            router.replace(`/chat/${seed.sessionId}`);
          }
        }
        if (seed.turnId) {
          setNextTurnId(seed.turnId);
        }

        setTurns([
          {
            id: seed.turnId ?? newTurnId(),
            level: "seed",
            source: "seed",
            question: seed.question,
            rationale: `${seed.domain_label} 분야의 첫 질문`,
            domainLabel: seed.domain_label,
            citations: seed.citations,
            createdAt: Date.now(),
          },
        ]);
      } catch (e) {
        if (ctrl.signal.aborted) return;
        setError(
          e instanceof Error
            ? `첫 질문 생성에 실패했습니다: ${e.message}`
            : "첫 질문 생성에 실패했습니다.",
        );
      } finally {
        if (!ctrl.signal.aborted) setSeeding(false);
      }
    })();

    return () => ctrl.abort();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propSessionId]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [turns.length, loading]);

  useEffect(() => {
    if (turns.length > 0 && !propSessionId) saveChatTurns(turns);
  }, [turns, propSessionId]);

  const currentTurn = turns.at(-1) ?? null;
  const awaitingAnswer = currentTurn !== null && currentTurn.answer === undefined;

  async function handleSubmit(overrideAnswer?: string) {
    if (!currentTurn || loading) return;
    const answer = overrideAnswer ?? draft;
    if (answer.trim().length === 0) return;
    setDraft("");
    setLoading(true);
    setLoadingMessage("답변을 받아 분석을 시작합니다…");
    setError(null);

    // Mark current turn as having an answer locally.
    setTurns((prev) =>
      prev.map((t) => (t.id === currentTurn.id ? { ...t, answer } : t)),
    );

    const updatedId = currentTurn.id;
    const currentDomain = currentTurn.domainLabel;
    const turnsSnapshot = turns;

    // Decided once `meta` arrives — drives whether we use the BE's streamed
    // follow-up or pivot to a fresh switchSeed after the stream finishes.
    let switchMode = false;
    // Placeholder turn id used to grow the streamed follow-up question. Swapped
    // for BE's pre-allocated next_turn_id in `onDone`.
    let nextTurnPlaceholderId: string | null = null;

    try {
      await submitInterviewStream(
        {
          question: currentTurn.question,
          answer,
          domains: selectedDomains.map((d) => d.label),
          keywords: customKeywords,
          material_ids: materialIds,
          sessionId: dbSessionId ?? undefined,
          turnId: nextTurnId ?? currentTurn.id,
        },
        {
          onStarted: ({ thread_id }) => {
            setTurns((prev) =>
              prev.map((t) =>
                t.id === updatedId ? { ...t, threadId: thread_id } : t,
              ),
            );
          },
          onStage: ({ message }) => {
            setLoadingMessage(message);
          },
          onMeta: (m) => {
            // Decide switch policy as soon as analyzer's verdict arrives.
            const depth = consecutiveFollowUpsOnDomain(turnsSnapshot, currentDomain);
            const depthExhausted =
              m.answer_quality === "good" && depth >= MAX_PROBE_DEPTH;
            switchMode =
              m.answer_quality === "uncertain" ||
              m.answer_quality === "incorrect" ||
              depthExhausted;

            // Hydrate analyzed turn so the analysis sidebar updates
            // immediately — user reads notes/intent while explanation streams.
            setTurns((prev) =>
              prev.map((t) =>
                t.id === updatedId
                  ? {
                      ...t,
                      notes: m.notes,
                      questionIntent: m.question_intent,
                      answerQuality: m.answer_quality,
                      score: m.score ?? undefined,
                      retrievedContext: m.retrieved_context,
                    }
                  : t,
              ),
            );
            setSelectedTurnId(updatedId);
          },
          onExplanationStart: () => {
            setTurns((prev) =>
              prev.map((t) =>
                t.id === updatedId ? { ...t, explanation: "" } : t,
              ),
            );
          },
          onExplanationDelta: (chunk) => {
            setTurns((prev) =>
              prev.map((t) =>
                t.id === updatedId
                  ? { ...t, explanation: (t.explanation ?? "") + chunk }
                  : t,
              ),
            );
          },
          onQuestionStart: () => {
            // In switch mode we'll spawn a fresh seed AFTER the stream ends —
            // skip the BE's follow-up entirely so the user never sees a
            // question that's about to be replaced.
            if (switchMode) return;
            const placeholderId = newTurnId();
            nextTurnPlaceholderId = placeholderId;
            setTurns((prev) => [
              ...prev,
              {
                id: placeholderId,
                level: "intermediate",
                source: "follow-up",
                question: "",
                rationale: "",
                domainLabel: currentDomain,
                citations: [],
                createdAt: Date.now(),
              },
            ]);
          },
          onQuestionDelta: (chunk) => {
            if (switchMode || !nextTurnPlaceholderId) return;
            const pid = nextTurnPlaceholderId;
            setTurns((prev) =>
              prev.map((t) =>
                t.id === pid
                  ? { ...t, question: (t.question ?? "") + chunk }
                  : t,
              ),
            );
          },
          onQuestionEnd: (qe) => {
            if (switchMode || !nextTurnPlaceholderId) return;
            const pid = nextTurnPlaceholderId;
            setTurns((prev) =>
              prev.map((t) =>
                t.id === pid
                  ? {
                      ...t,
                      level: (qe.level as Turn["level"]) || "intermediate",
                      rationale: qe.rationale,
                      domainLabel: qe.domain_label || currentDomain,
                      citations: qe.citations,
                    }
                  : t,
              ),
            );
          },
          onDone: (d: StreamDone) => {
            if (d.session_id) {
              setDbSessionId(d.session_id);
              setActiveSessionId(d.session_id);
            }
            if (d.next_turn_id) {
              setNextTurnId(d.next_turn_id);
              if (!switchMode && nextTurnPlaceholderId) {
                const placeholder = nextTurnPlaceholderId;
                setTurns((prev) =>
                  prev.map((t) =>
                    t.id === placeholder
                      ? { ...t, id: d.next_turn_id ?? placeholder }
                      : t,
                  ),
                );
              }
            }
          },
          onError: (msg) => {
            setError(`스트리밍 실패: ${msg}`);
          },
        },
      );

      // Switch path — spawn a fresh seed on a different domain after the
      // stream finished writing the explanation.
      if (switchMode) {
        setLoadingMessage("새 분야 질문을 가져오는 중…");
        let otherDomainLabels = selectedDomains
          .map((d) => d.label)
          .filter((l) => l !== currentDomain);
        let otherKeywords = customKeywords.filter((k) => k !== currentDomain);
        if (otherDomainLabels.length === 0 && otherKeywords.length === 0) {
          otherDomainLabels = selectedDomains.map((d) => d.label);
          otherKeywords = customKeywords;
        }
        try {
          const askedSoFar = Array.from(
            new Set(turns.map((t) => t.question).filter(Boolean)),
          );
          askedSoFar.push(currentTurn.question);
          const switchSeed = await generateSeedQuestion({
            track: onboarding!.track,
            domains: otherDomainLabels,
            keywords: otherKeywords,
            exclude_questions: askedSoFar,
            material_ids: materialIds,
            sessionId: dbSessionId ?? undefined,
          });
          const isActualSwitch =
            !!currentDomain && switchSeed.domain_label !== currentDomain;
          const switchTurnId = switchSeed.turnId ?? newTurnId();
          if (switchSeed.turnId) setNextTurnId(switchSeed.turnId);
          setTurns((prev) => [
            ...prev,
            {
              id: switchTurnId,
              level: "seed",
              source: isActualSwitch ? "domain-switch" : "seed",
              question: switchSeed.question,
              rationale: isActualSwitch
                ? `${switchSeed.domain_label} 분야로 넘어갑니다.`
                : `${switchSeed.domain_label} 분야의 다음 질문`,
              domainLabel: switchSeed.domain_label,
              citations: switchSeed.citations,
              createdAt: Date.now(),
            },
          ]);
        } catch {
          // switchSeed failed — user can re-trigger via UI; non-fatal.
        }
      }
    } catch (e) {
      // Stream failure → fall back to the non-streaming endpoint so the
      // user isn't stranded.
      try {
        const fallback = await submitInterview({
          question: currentTurn.question,
          answer,
          domains: selectedDomains.map((d) => d.label),
          keywords: customKeywords,
          material_ids: materialIds,
          sessionId: dbSessionId ?? undefined,
          turnId: nextTurnId ?? currentTurn.id,
        });
        if (fallback.sessionId) {
          setDbSessionId(fallback.sessionId);
          setActiveSessionId(fallback.sessionId);
        }
        if (fallback.nextTurnId !== undefined) setNextTurnId(fallback.nextTurnId);
        setTurns((prev) =>
          prev.map((t) =>
            t.id === updatedId
              ? {
                  ...t,
                  notes: fallback.notes,
                  followUps: fallback.followUps,
                  answerQuality: fallback.answerQuality,
                  explanation: fallback.explanation,
                  questionIntent: fallback.questionIntent,
                  score: fallback.score,
                  retrievedContext: fallback.retrievedContext,
                  threadId: fallback.threadId,
                  status: fallback.status,
                }
              : t,
          ),
        );
        const probe = fallback.followUps[0];
        if (probe) {
          const probeTurnId = fallback.nextTurnId ?? newTurnId();
          setTurns((prev) => [
            ...prev,
            {
              id: probeTurnId,
              level: probe.level,
              source: "follow-up",
              question: probe.text,
              rationale: probe.rationale,
              domainLabel: probe.domain_label || currentTurn.domainLabel,
              citations: probe.citations,
              createdAt: Date.now(),
            },
          ]);
        }
      } catch (e2) {
        setError(e2 instanceof Error ? e2.message : "분석에 실패했습니다.");
        setTurns((prev) =>
          prev.map((t) =>
            t.id === currentTurn.id ? { ...t, answer: undefined } : t,
          ),
        );
        setDraft(answer);
      }
    } finally {
      setLoading(false);
      setLoadingMessage(null);
    }
  }

  if (seeding) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-md">
          <span className="h-2 w-2 rounded-full bg-rausch animate-pulse" />
          <p className="text-body-sm text-muted">
            {propSessionId
              ? "면접 기록을 불러오는 중…"
              : "면접관이 첫 질문을 준비 중입니다…"}
          </p>
        </div>
      </main>
    );
  }

  if (turns.length === 0 && error) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <div className="rounded-md border border-rausch bg-rausch/5 text-error-text p-lg max-w-md text-center">
          <p className="text-body-md">{error}</p>
          <button
            type="button"
            onClick={() => router.push("/onboarding")}
            className="btn-secondary mt-md"
          >
            다시 시도
          </button>
        </div>
      </main>
    );
  }

  const totalScopeCount =
    (selectedDomains.length + customKeywords.length) ||
    (onboarding?.domainIds.length ?? 0) + (onboarding?.customKeywords?.length ?? 0);

  const activeSidId = dbSessionId ?? propSessionId;

  return (
    <main className="flex-1 min-h-0 bg-canvas overflow-hidden">
      <div className="h-full flex flex-col min-h-0">
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[280px_1fr_360px]">
          {/* Sidebar */}
          <SessionSidebar activeSessionId={activeSidId ?? undefined} />

          {/* Main chat column */}
          <div className="flex flex-col min-h-0 h-full px-xl py-md">
            {/* Session strip */}
            {onboarding && (
              <div className="flex flex-wrap items-center justify-between gap-md pb-sm shrink-0">
                <p className="text-body-sm text-muted">
                  {onboarding.track === "cs" ? "CS 기초" : "기술 스택"} ·{" "}
                  {totalScopeCount === 1
                    ? selectedDomains[0]?.label ?? customKeywords[0] ?? onboarding.customKeywords?.[0]
                    : `${totalScopeCount}개 주제`}
                </p>
              </div>
            )}

            <div className="flex flex-col min-h-0 h-full flex-1">
              <div
                ref={scrollRef}
                className="flex-1 min-h-0 overflow-y-auto scrollbar-thin pr-sm flex flex-col gap-md pb-md"
                style={{ scrollbarGutter: "stable" }}
              >
                {turns.map((turn) => (
                  <ConversationTurn key={turn.id} turn={turn} />
                ))}

                {loading && (
                  <div className="flex gap-md">
                    <span className="h-10 w-10 rounded-full bg-canvas border border-hairline flex items-center justify-center text-ink shrink-0">
                      <Icon name="hourglass_top" size={18} />
                    </span>
                    <div className="rounded-md border border-hairline bg-surface-soft p-md flex items-center gap-md">
                      <span className="h-2 w-2 rounded-full bg-rausch animate-pulse" />
                      <p className="text-body-sm text-muted">
                        {loadingMessage ?? "답변을 분석하고 다음 꼬리 질문을 준비 중…"}
                      </p>
                    </div>
                  </div>
                )}

                {error && turns.length > 0 && (
                  <p className="rounded-md border border-rausch bg-rausch/5 text-error-text p-md text-body-sm">
                    {error}
                  </p>
                )}
              </div>

              <div className="pt-sm shrink-0">
                {awaitingAnswer ? (
                  <Composer
                    value={draft}
                    onChange={setDraft}
                    onSubmit={() => handleSubmit()}
                    onDontKnow={() => handleSubmit("잘 모르겠습니다")}
                    loading={loading}
                    placeholder="답변을 입력하고 Enter (Shift+Enter 줄바꿈)"
                  />
                ) : null}
              </div>
            </div>
          </div>

          {/* Analysis rail */}
          <div className="hidden lg:block min-h-0 h-full pt-md pr-xl pb-md">
            <AnalysisRail
              turns={turns}
              selectedTurnId={selectedTurnId}
              onSelect={setSelectedTurnId}
              domains={selectedDomains}
              keywords={customKeywords}
              sessionMaterials={sessionMaterials}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
