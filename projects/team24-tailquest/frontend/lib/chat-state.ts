// Chat turn shape — what the chat page operates on.
// Each turn is one Q (from interviewer) + optional A (from user) + optional analysis (from backend).

import type { AnalysisNote, AnswerQuality, Chunk, Citation, FeedbackAction, FollowUpQuestion, SessionStatus } from "@/lib/api";

export type Level = "basic" | "intermediate" | "advanced";

export interface Turn {
  id: string;
  /** "seed" / "switch" for fresh-domain turns; otherwise the level used */
  level: Level | "seed";
  /** Domain id this turn belongs to (legacy — domainLabel is preferred) */
  domainId?: string;
  /** Domain or keyword label this turn covers (e.g. "운영체제", "Kubernetes").
   *  Used to detect single-domain stagnation and force rotation. */
  domainLabel?: string;
  /** Source of this question:
   *   "seed"          — onboarding starter
   *   "follow-up"     — drilled into previous answer
   *   "domain-switch" — forced rotation when previous N turns were one domain */
  source: "seed" | "follow-up" | "domain-switch";
  question: string;
  rationale?: string;
  answer?: string;
  notes?: AnalysisNote[];
  /** Backend's classification of the user's answer for this turn. */
  answerQuality?: AnswerQuality;
  /** Friendly explanation rendered after the answer when quality !== "good".
   *  Triggers a domain switch in the next interviewer turn. */
  explanation?: string;
  /** What the interviewer's question is checking for — shown in the analysis rail. */
  questionIntent?: string;
  score?: number;
  followUps?: FollowUpQuestion[];
  /** RAG chunks retrieved when this turn was analyzed. */
  retrievedContext?: Chunk[];
  /** Citations attached to this question (from the FollowUpQuestion that produced it). */
  citations?: Citation[];
  /** LangGraph thread ID for HITL feedback — set after submitInterview responds. */
  threadId?: string;
  /** Workflow status from backend. "awaiting_feedback" → show FeedbackBar. */
  status?: SessionStatus;
  /** History of feedback actions sent in this turn — used to disable FeedbackBar
   *  after repeated attempts and to prevent double-click races. */
  feedbackHistory?: { action: FeedbackAction; at: number }[];
  createdAt: number;
}

export function newTurnId(): string {
  return `t_${Math.random().toString(36).slice(2, 9)}`;
}

// ----- Turns persistence (survive refresh) -----
// Stored in sessionStorage (per-tab) so a refresh in /chat restores the
// in-progress interview instead of seeding a fresh question. Cleared on
// /onboarding mount, which is treated as "starting a new session".

const TURNS_KEY = "tq:chat_turns";

export function loadChatTurns(): Turn[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(TURNS_KEY);
    return raw ? (JSON.parse(raw) as Turn[]) : [];
  } catch {
    return [];
  }
}

export function saveChatTurns(turns: Turn[]): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(TURNS_KEY, JSON.stringify(turns));
  } catch {
    // Quota exceeded or serialization issue — silently drop. The next
    // refresh will lose history but the current session continues.
  }
}

export function clearChatTurns(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(TURNS_KEY);
}
