// Backend API client. The Next config rewrites /api/backend/* → http://localhost:8000/*
//
// Default behavior:
//   - Try the real backend first (FastAPI on :8000).
//   - On network failure or non-2xx, fall back to a *content-aware* local mock
//     so the UI keeps working during dev without manual env-var fiddling.
//
// Forced override (for Storybook / offline dev): set NEXT_PUBLIC_USE_MOCK=true.

import { authFetch } from "./auth-fetch";

export type Severity = "minor" | "moderate" | "critical";

export interface AnalysisNote {
  label: string;
  detail?: string;
  quote?: string;
  severity: Severity;
}

export interface Chunk {
  text: string;
  source: "public" | "user" | "web";
  file_name: string;
  heading: string;
  score: number;
  url?: string;
}

export interface Citation {
  file_name: string;
  heading: string;
  excerpt: string;
  url?: string;
}

export type MaterialKind = "md" | "pdf" | "github";
export type MaterialStatus = "indexing" | "ready" | "failed";

export interface MaterialResponse {
  id: string;
  name: string;
  kind: MaterialKind;
  status: MaterialStatus;
  chunks: number;
  error?: string;
}

export interface FollowUpQuestion {
  level: "basic" | "intermediate" | "advanced";
  text: string;
  rationale?: string;
  source?: string;
  /** Which domain or keyword this follow-up belongs to.
   *  Used by the chat shell to detect single-domain stagnation and force a switch. */
  domain_label?: string;
  /** Source citations from retrieved RAG context — present only when the
   *  question was informed by user-uploaded or public reference material. */
  citations?: Citation[];
}

export type AnswerQuality = "good" | "uncertain" | "incorrect";

export type FeedbackAction = "regenerate" | "refine_easier" | "refine_harder" | "accept";

export type SessionStatus = "awaiting_feedback" | "final";

export interface SessionResult {
  question: string;
  answer: string;
  notes: AnalysisNote[];
  followUps: FollowUpQuestion[];
  /** Backend's judgment of the answer.
   *  When uncertain or incorrect, the chat shell shows the explanation and
   *  pivots to a different domain for the next question. */
  answerQuality?: AnswerQuality;
  /** Friendly interviewer-tone explanation, set only when answerQuality !== "good". */
  explanation?: string;
  /** What the question intends to evaluate — always populated regardless of
   *  answer quality. Rendered in the analysis rail in place of candidate
   *  follow-ups so the user can self-reflect on what was being tested. */
  questionIntent?: string;
  score?: number;
  /** RAG chunks retrieved for this turn — surfaced in the analysis rail. */
  retrievedContext?: Chunk[];
  /** Thread ID issued by the backend for HITL feedback loop. */
  threadId?: string;
  /** Workflow status: "awaiting_feedback" → FeedbackBar visible; "final" → done. */
  status?: SessionStatus;
  /** DB session ID — used to update URL and sessionStorage. */
  sessionId?: string;
  /** Pre-allocated ID for the next turn (followUps[0] pre-inserted by BE). */
  nextTurnId?: string | null;
}

export interface SessionSummary {
  id: string;
  track: string;
  title: string;
  domains: string[];
  keywords: string[];
  materialIds: string[];
  turnCount: number;
  lastScore: number | null;
  createdAt: number;
  updatedAt: number;
}

export interface TurnDetail {
  id: string;
  seq: number;
  level: string;
  source: string;
  domainLabel: string;
  question: string;
  rationale: string;
  answer: string | null;
  notes: AnalysisNote[];
  followUps: FollowUpQuestion[];
  retrievedContext: Chunk[];
  citations: Citation[];
  answerQuality: string;
  explanation: string;
  questionIntent: string;
  score: number | null;
  threadId: string | null;
  createdAt: number;
}

export interface SessionDetail extends SessionSummary {
  turns: TurnDetail[];
}

export interface SubmitPayload {
  question: string;
  answer: string;
  /** Selected domain labels from onboarding — passed so the backend can broaden
   *  follow-up question scope across all selected domains. */
  domains?: string[];
  /** Free-form keywords from onboarding — same treatment as domains. */
  keywords?: string[];
  /** IDs of user-uploaded materials to include in RAG retrieval.
   *  Empty or omitted → public collection only. */
  material_ids?: string[];
  /** DB session ID — when present, BE writes answer to the correct session row. */
  sessionId?: string;
  /** DB turn ID — when present, BE writes to the specific turn row. */
  turnId?: string;
}

export interface SeedPayload {
  track: "cs" | "stack";
  domains: string[];
  keywords: string[];
  /** Already-asked question texts in this session — backend uses them so the
   *  generated seed isn't a duplicate (e.g. always re-asking "프로세스와 스레드"). */
  exclude_questions?: string[];
  /** IDs of user-uploaded materials. When non-empty, backend mines a topic
   *  from those materials and returns citations. */
  material_ids?: string[];
  /** When present, appends a new seed turn to an existing session. */
  sessionId?: string;
}

export interface SeedResult {
  question: string;
  /** Which domain or keyword the seed question was drawn from */
  domain_label: string;
  /** Source citations when the seed was generated from user materials.
   *  Empty for static-pool seeds. */
  citations?: Citation[];
  /** DB session ID issued (or reused) by BE. */
  sessionId?: string;
  /** DB turn ID for this seed turn. */
  turnId?: string;
}

const FORCE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

export async function submitInterview(
  payload: SubmitPayload,
): Promise<SessionResult> {
  if (FORCE_MOCK) return mockResult(payload);

  const res = await authFetch("/api/backend/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: payload.question,
      answer: payload.answer,
      domains: payload.domains ?? [],
      keywords: payload.keywords ?? [],
      material_ids: payload.material_ids ?? [],
      sessionId: payload.sessionId,
      turnId: payload.turnId,
    }),
  });
  if (!res.ok) throw new Error(`Backend ${res.status}: ${await res.text()}`);
  const data = await res.json();
  if (data.evaluation?.score != null && data.score == null) {
    data.score = Math.round(data.evaluation.score * 100);
  }
  if (data.score == null) data.score = 70;
  return data;
}

// ---------- Streaming submit ----------

export interface StreamMeta {
  answer_quality: AnswerQuality;
  question_intent: string;
  notes: AnalysisNote[];
  retrieved_context: Chunk[];
  score: number | null;
}

export interface StreamQuestionEnd {
  level: string;
  rationale: string;
  domain_label: string;
  citations: Citation[];
}

export interface StreamDoneFollowUp {
  level: string;
  text: string;
  rationale: string;
  domain_label: string;
  citations: Citation[];
}

export interface StreamDone {
  session_id: string;
  turn_id: string;
  next_turn_id: string | null;
  thread_id: string;
  answer_quality: AnswerQuality;
  explanation: string;
  question_intent: string;
  score: number | null;
  notes: AnalysisNote[];
  follow_ups: StreamDoneFollowUp[];
  retrieved_context: Chunk[];
  status: SessionStatus;
}

export interface StreamHandlers {
  onStarted?: (data: { thread_id: string }) => void;
  onStage?: (data: { step: string; message: string }) => void;
  onMeta?: (data: StreamMeta) => void;
  onExplanationStart?: () => void;
  onExplanationDelta?: (text: string) => void;
  onExplanationEnd?: () => void;
  onQuestionStart?: () => void;
  onQuestionDelta?: (text: string) => void;
  onQuestionEnd?: (data: StreamQuestionEnd) => void;
  onDone?: (data: StreamDone) => void;
  onError?: (message: string) => void;
}

/** POST /sessions/stream — Server-Sent Events.
 *
 *  fetch + ReadableStream rather than EventSource because the latter is
 *  GET-only and we need to POST the answer body. SSE wire format is hand-
 *  parsed: blocks separated by \n\n, each block has `event:` and `data:`
 *  lines. The matching backend endpoint is `app/api/sessions.py:stream_session`.
 *
 *  `signal` lets the caller abort the stream if the user navigates away. */
export async function submitInterviewStream(
  payload: SubmitPayload,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await authFetch("/api/backend/sessions/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({
      question: payload.question,
      answer: payload.answer,
      domains: payload.domains ?? [],
      keywords: payload.keywords ?? [],
      material_ids: payload.material_ids ?? [],
      sessionId: payload.sessionId,
      turnId: payload.turnId,
    }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Stream ${res.status}: ${await res.text().catch(() => "")}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (event: string, data: unknown) => {
    const d = (data ?? {}) as Record<string, unknown>;
    switch (event) {
      case "started":
        handlers.onStarted?.(d as { thread_id: string });
        break;
      case "stage":
        handlers.onStage?.(d as { step: string; message: string });
        break;
      case "meta":
        handlers.onMeta?.(d as unknown as StreamMeta);
        break;
      case "explanation_start":
        handlers.onExplanationStart?.();
        break;
      case "explanation_delta":
        handlers.onExplanationDelta?.((d.text as string) ?? "");
        break;
      case "explanation_end":
        handlers.onExplanationEnd?.();
        break;
      case "question_start":
        handlers.onQuestionStart?.();
        break;
      case "question_delta":
        handlers.onQuestionDelta?.((d.text as string) ?? "");
        break;
      case "question_end":
        handlers.onQuestionEnd?.(d as unknown as StreamQuestionEnd);
        break;
      case "done":
        handlers.onDone?.(d as unknown as StreamDone);
        break;
      case "error":
        handlers.onError?.((d.message as string) ?? "stream error");
        break;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      if (!block.trim()) continue;
      let eventName = "message";
      const dataLines: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      }
      let data: unknown = {};
      try {
        data = JSON.parse(dataLines.join("\n") || "{}");
      } catch {
        // bad JSON — skip
      }
      dispatch(eventName, data);
    }
  }
}

// ---------- Session history ----------

export async function listSessions(): Promise<SessionSummary[]> {
  try {
    const res = await authFetch("/api/backend/sessions");
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  } catch {
    return [];
  }
}

export async function getSession(id: string): Promise<SessionDetail> {
  const res = await authFetch(`/api/backend/sessions/${id}`);
  if (!res.ok) throw new Error(`Backend ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  const res = await authFetch(`/api/backend/sessions/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error(await res.text());
}

export async function renameSession(id: string, title: string): Promise<SessionSummary> {
  const res = await authFetch(`/api/backend/sessions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Backend ${res.status}: ${await res.text()}`);
  return res.json();
}

// ---------- Materials (RAG resource management) ----------
// These never fall back to mock — failures must be visible to the user.

export async function uploadMaterial(file: File): Promise<MaterialResponse> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await authFetch("/api/backend/materials/upload", {
    method: "POST",
    body: fd,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listMaterials(): Promise<MaterialResponse[]> {
  const res = await authFetch("/api/backend/materials");
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getMaterial(id: string): Promise<MaterialResponse> {
  const res = await authFetch(`/api/backend/materials/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteMaterial(id: string): Promise<void> {
  const res = await authFetch(`/api/backend/materials/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error(await res.text());
}

export async function ingestGithub(repoUrl: string): Promise<MaterialResponse> {
  const res = await authFetch("/api/backend/materials/github", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ---------- Local content-aware mock ----------

const QUESTION_TAILS = [
  "에 대해 설명해주세요",
  "을 설명해주세요",
  "를 설명해주세요",
  "을 설명해 주세요",
  "를 설명해 주세요",
  "은 무엇입니까",
  "는 무엇입니까",
  "을 비교해주세요",
  "를 비교해주세요",
  "은 어떻게 처리하시겠습니까",
  "는 어떻게 처리하시겠습니까",
  "은 무엇인가요",
  "는 무엇인가요",
];

function extractTopic(question: string): string {
  let cleaned = question.trim().replace(/[?.!]+$/, "");
  for (const tail of QUESTION_TAILS) {
    if (cleaned.endsWith(tail)) {
      cleaned = cleaned.slice(0, -tail.length).replace(/[?.!\s]+$/, "");
      break;
    }
  }
  return cleaned || question;
}

function keyTerm(question: string): string {
  const topic = extractTopic(question);
  for (const marker of ["의 차이", "의 동작", "의 원리", "의 구조"]) {
    if (topic.includes(marker)) return topic.split(marker)[0].trim();
  }
  const words = topic.split(/\s+/);
  return words.slice(0, 3).join(" ").trim() || topic;
}

// ---------- Seed question generator ----------

export async function generateSeedQuestion(
  payload: SeedPayload,
): Promise<SeedResult> {
  if (FORCE_MOCK) return mockSeed(payload);
  const res = await authFetch("/api/backend/sessions/seed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      track: payload.track,
      domains: payload.domains,
      keywords: payload.keywords,
      exclude_questions: payload.exclude_questions ?? [],
      material_ids: payload.material_ids ?? [],
      sessionId: payload.sessionId,
    }),
  });
  if (!res.ok) throw new Error(`Backend ${res.status}: ${await res.text()}`);
  return await res.json();
}

function mockSeed(p: SeedPayload): SeedResult {
  const candidates: SeedResult[] = [];
  for (const d of p.domains) {
    candidates.push({
      question: `${d}의 핵심 개념 중 자신 있는 부분 하나를 골라 설명해주세요.`,
      domain_label: d,
    });
  }
  for (const kw of p.keywords) {
    candidates.push({
      question: `${kw}에 대해 알고 계신 내용을 자유롭게 설명해주세요.`,
      domain_label: kw,
    });
  }
  if (candidates.length === 0) {
    return {
      question: "자기소개와 함께 가장 자신 있는 기술 영역을 한 가지 말씀해주세요.",
      domain_label: "일반",
      sessionId: `s_mock_${Math.random().toString(36).slice(2, 10)}`,
      turnId: `t_mock_${Math.random().toString(36).slice(2, 10)}`,
    };
  }
  const excluded = new Set(p.exclude_questions ?? []);
  const fresh = candidates.filter((c) => !excluded.has(c.question));
  const pool = fresh.length > 0 ? fresh : candidates;
  const chosen = pool[Math.floor(Math.random() * pool.length)];
  return {
    ...chosen,
    sessionId: p.sessionId ?? `s_mock_${Math.random().toString(36).slice(2, 10)}`,
    turnId: `t_mock_${Math.random().toString(36).slice(2, 10)}`,
  };
}

const DONT_KNOW_PHRASES = [
  "잘 모르겠",
  "잘 모릅",
  "모르겠습",
  "모르겠어",
  "처음 들어",
  "기억이 안",
];

async function mockResult(p: SubmitPayload): Promise<SessionResult> {
  await new Promise((r) => setTimeout(r, 700));
  const topic = extractTopic(p.question);
  const key = keyTerm(p.question);
  const cleaned = p.answer.trim();
  const uncertain =
    DONT_KNOW_PHRASES.some((ph) => cleaned.includes(ph)) || cleaned.length < 30;

  const mockTid = `th_mock_${Math.random().toString(36).slice(2, 8)}`;

  if (uncertain) {
    return {
      question: p.question,
      answer: p.answer,
      answerQuality: "uncertain",
      explanation: `${topic}에 대해 짧게 설명드리면, 핵심 개념을 한 문장으로 정리할 수 있을 정도면 신입 면접에서는 충분합니다. 다음 질문은 알고 계신 분야로 넘어가볼게요.`,
      notes: [
        {
          label: "답변 부재 — 잘 모르겠다고 응답",
          detail: "해당 주제에 대한 답변이 충분히 제시되지 않았습니다.",
          severity: "critical",
        },
      ],
      followUps: [],
      sessionId: p.sessionId ?? `s_mock_${Math.random().toString(36).slice(2, 10)}`,
      threadId: mockTid,
      status: "awaiting_feedback",
    };
  }

  return {
    question: p.question,
    answer: p.answer,
    answerQuality: "good",
    explanation: "",
    score: 72,
    sessionId: p.sessionId ?? `s_mock_${Math.random().toString(36).slice(2, 10)}`,
    nextTurnId: `t_mock_${Math.random().toString(36).slice(2, 10)}`,
    notes: [
      {
        label: `내부 메커니즘 설명 부족 — ${topic}`,
        detail:
          "정의 수준의 답변에 머물러, 면접관이 기대하는 동작 원리·구현 디테일·자료구조 레벨의 설명이 빠졌습니다.",
        severity: "moderate",
      },
      {
        label: "실무 트레이드오프와 대안 부재",
        detail:
          "언제 사용하고 언제 피해야 하는지, 다른 선택지와의 비교가 답변에 드러나지 않습니다.",
        severity: "moderate",
      },
      {
        label: "구체적 예시·코드 레벨 시나리오 누락",
        detail:
          "개념 위주로 서술되어 실제 사용 사례나 발생 가능한 문제 상황이 제시되지 않았습니다.",
        severity: "minor",
      },
    ],
    followUps: [
      {
        level: "basic",
        text: `${key}의 동작을 더 구체적인 예시와 함께 설명해주세요.`,
        rationale: `답변에서 '${topic}'가 정의 수준으로만 다뤄진 부분에 대한 깊이 검증`,
      },
      {
        level: "intermediate",
        text: `${key}를 사용할 때 발생할 수 있는 대표적인 문제와 해결 방법은 무엇인가요?`,
        rationale: "실무에서 마주치는 트레이드오프·엣지 케이스 검증",
      },
      {
        level: "advanced",
        text: `${key}가 시스템 성능·확장성에 어떤 영향을 주는지 시스템 레벨에서 설명해주세요.`,
        rationale: "시스템 설계 관점·실무 사례 검증",
      },
    ],
    threadId: mockTid,
    status: "awaiting_feedback",
  };
}

