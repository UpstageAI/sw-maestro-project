// 백엔드(FastAPI + LangGraph) 연동 클라이언트.
// 백엔드 응답 스키마(snake_case) → 프론트 도메인 타입(camelCase) 매퍼 포함.

import type {
  AgentOpinion,
  ConsultationSession,
  DiscussionMessage,
  DiscussionRound,
  FinalResult,
} from '@/types';
import type { AgentId } from '@/types/agent';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

// ─── 백엔드 응답 타입 (느슨하게 정의 — 필요한 필드만) ───────────────

interface BackendAgentMessage {
  id: string;
  agent_id: AgentId;
  agent_name: string;
  round: 'round_1' | 'round_2' | 'round_3';
  // round 1
  advice?: string;
  rationale?: string;
  stance?: AgentOpinion['stance'];
  key_points?: string[];
  // round 2
  statement?: string;
  targets?: Array<{
    target_message_id: string;
    target_agent_id: AgentId;
    agreement: 'agree' | 'partial' | 'disagree' | 'extend';
  }>;
  // round 3
  final_stance?: AgentOpinion['stance'];
  final_advice?: string;
  action_items?: string[];
}

interface BackendRound {
  round: 'round_1' | 'round_2' | 'round_3';
  started_at?: string;
  completed_at?: string;
  messages: BackendAgentMessage[];
  supervisor_note?: unknown;
}

interface BackendActionItem {
  title: string;
  detail: string;
  timing: 'immediate' | 'short_term' | 'long_term';
}

interface BackendFinalPayload {
  situation: string;
  disagreements: string[];
  final_advice: string;
  action_items: BackendActionItem[];
  caveats: string[];
  contributing_agents?: AgentId[];
}

export interface BackendConsultationResponse {
  consultation_id: string;
  status:
    | 'pending'
    | 'analyzing'
    | 'round_1_running'
    | 'summary_1_running'
    | 'round_2_running'
    | 'classify_2_running'
    | 'round_3_running'
    | 'summarizing'
    | 'completed'
    | 'terminated'
    | 'failed';
  user_question: string;
  rounds?: BackendRound[];
  final?: BackendFinalPayload;
  errors?: Array<{ code: string; user_message_key: string }>;
}

// ─── HTTP ────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

// 브라우저·Node 모두에서 동작. 폴리필 필요한 구형 환경은 PoC 범위 밖.
function newConsultationId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  // 매우 보수적 폴백 (실제로는 거의 안 탐).
  const hex = (n: number) =>
    Math.floor(Math.random() * 16 ** n)
      .toString(16)
      .padStart(n, '0');
  return `${hex(8)}-${hex(4)}-4${hex(3)}-8${hex(3)}-${hex(12)}`;
}

// ─── 엔드포인트 ──────────────────────────────────────────────────────

export async function startConsultation(userQuestion: string): Promise<string> {
  const consultation_id = newConsultationId();
  await request<{ consultation_id: string; status: string }>('/consultations', {
    method: 'POST',
    body: JSON.stringify({
      consultation_id,
      user_question: userQuestion,
      language: 'ko-KR',
    }),
  });
  return consultation_id;
}

export async function getConsultation(
  consultationId: string,
): Promise<BackendConsultationResponse> {
  return request<BackendConsultationResponse>(`/consultations/${consultationId}`);
}

interface BackendPunchline {
  chosen_agent_id: string;
  one_liner: string;
  vibe: 'harsh' | 'hopeful' | 'chaotic' | 'cold';
  rationale: string;
}

export async function requestPunchline(consultationId: string): Promise<BackendPunchline> {
  return request<BackendPunchline>(`/consultations/${consultationId}/punchline`, {
    method: 'POST',
  });
}

const TERMINAL_STATUSES = new Set<BackendConsultationResponse['status']>([
  'completed',
  'terminated',
  'failed',
]);

export async function pollUntilTerminal(
  consultationId: string,
  onProgress?: (status: BackendConsultationResponse['status']) => void,
  options?: { intervalMs?: number; timeoutMs?: number },
): Promise<BackendConsultationResponse> {
  const intervalMs = options?.intervalMs ?? 1500;
  const timeoutMs = options?.timeoutMs ?? 5 * 60 * 1000;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const res = await getConsultation(consultationId);
    onProgress?.(res.status);
    if (TERMINAL_STATUSES.has(res.status)) return res;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new ApiError(408, '상담 응답 대기 시간이 초과되었습니다.');
}

// ─── SSE 구독 ────────────────────────────────────────────────────────

export type BackendRoundName = 'round_1' | 'round_2' | 'round_3';

export interface PublicError {
  code: string;
  user_message_key: string;
  affected_agent?: AgentId;
}

export interface StreamEventHandlers {
  onStatusChanged?: (status: BackendConsultationResponse['status']) => void;
  onAnalysisCompleted?: (analysis: unknown) => void;
  onAgentMessage?: (round: BackendRoundName, message: BackendAgentMessage) => void;
  onSupervisorNote?: (note: unknown) => void;
  onCompleted?: (response: BackendConsultationResponse) => void;
  onError?: (error: PublicError | { message: string }) => void;
  onClose?: () => void;
}

/**
 * 백엔드의 GET /consultations/{id}/events SSE 스트림을 구독한다.
 * 반환값은 cleanup 함수 — 호출하면 EventSource를 닫는다.
 * 백엔드가 terminal 이벤트(completed / error_occurred)를 보내면 자동으로 닫힌다.
 */
export function subscribeEvents(
  consultationId: string,
  handlers: StreamEventHandlers,
): () => void {
  const url = `${API_BASE}/consultations/${consultationId}/events`;
  const source = new EventSource(url);
  let closed = false;

  const close = () => {
    if (closed) return;
    closed = true;
    source.close();
    handlers.onClose?.();
  };

  const parsePayload = (e: Event): { payload: Record<string, unknown> } | null => {
    try {
      const data = JSON.parse((e as MessageEvent).data);
      return data && typeof data === 'object' ? (data as { payload: Record<string, unknown> }) : null;
    } catch {
      return null;
    }
  };

  source.addEventListener('status_changed', (e) => {
    const d = parsePayload(e);
    const status = d?.payload?.status as BackendConsultationResponse['status'] | undefined;
    if (status) handlers.onStatusChanged?.(status);
  });

  source.addEventListener('analysis_completed', (e) => {
    const d = parsePayload(e);
    if (d?.payload?.analysis) handlers.onAnalysisCompleted?.(d.payload.analysis);
  });

  source.addEventListener('agent_message_added', (e) => {
    const d = parsePayload(e);
    const round = d?.payload?.round as BackendRoundName | undefined;
    const message = d?.payload?.message as BackendAgentMessage | undefined;
    if (round && message) handlers.onAgentMessage?.(round, message);
  });

  source.addEventListener('supervisor_note_added', (e) => {
    const d = parsePayload(e);
    if (d?.payload?.note) handlers.onSupervisorNote?.(d.payload.note);
  });

  source.addEventListener('completed', (e) => {
    const d = parsePayload(e);
    const response = d?.payload?.response as BackendConsultationResponse | undefined;
    if (response) handlers.onCompleted?.(response);
    close();
  });

  source.addEventListener('error_occurred', (e) => {
    const d = parsePayload(e);
    const err = (d?.payload?.error as PublicError | undefined) ?? {
      message: '상담 실행 중 오류가 발생했습니다.',
    };
    handlers.onError?.(err);
    close();
  });

  source.onerror = () => {
    // EventSource 자동 재연결 시도 중이거나 종료 상태. CLOSED면 cleanup.
    if (source.readyState === EventSource.CLOSED) {
      if (!closed) handlers.onError?.({ message: 'SSE 연결이 끊어졌습니다.' });
      close();
    }
  };

  return close;
}

// ─── 단일 메시지 매퍼 (SSE 이벤트 단위 처리용) ───────────────────────

export function toOpinion(m: BackendAgentMessage): AgentOpinion {
  return {
    agentId: m.agent_id,
    advice: m.advice ?? '',
    rationale: m.rationale ?? '',
    stance: m.stance ?? 'mixed',
  };
}

export function toDiscussionMessage(
  m: BackendAgentMessage,
  label: 'rebuttal' | 'deepdive',
): DiscussionMessage {
  const content = label === 'rebuttal' ? (m.statement ?? '') : (m.final_advice ?? '');
  const replyTo = m.targets?.[0]?.target_agent_id;
  return {
    agentId: m.agent_id,
    content,
    messageType: label,
    ...(replyTo ? { replyToAgentId: replyTo } : {}),
  };
}

// ─── 매퍼: 백엔드 응답 → 프론트 ConsultationSession ──────────────────

function findRound(
  rounds: BackendRound[] | undefined,
  name: BackendRound['round'],
): BackendRound | undefined {
  return rounds?.find((r) => r.round === name);
}

function mapOpinions(round1: BackendRound | undefined): AgentOpinion[] {
  if (!round1) return [];
  return round1.messages.map((m) => ({
    agentId: m.agent_id,
    advice: m.advice ?? '',
    rationale: m.rationale ?? '',
    stance: m.stance ?? 'mixed',
  }));
}

// 2라운드(반박)는 'rebuttal', 3라운드(최종 입장)는 'deepdive' 라벨로 표시.
function mapDiscussionRound(
  backend: BackendRound | undefined,
  label: 'rebuttal' | 'deepdive',
): DiscussionMessage[] {
  if (!backend) return [];
  return backend.messages.map((m) => {
    const content = label === 'rebuttal' ? (m.statement ?? '') : (m.final_advice ?? '');
    const replyTo = m.targets?.[0]?.target_agent_id;
    return {
      agentId: m.agent_id,
      content,
      messageType: label,
      ...(replyTo ? { replyToAgentId: replyTo } : {}),
    };
  });
}

function mapFinal(payload: BackendFinalPayload | undefined): FinalResult | null {
  if (!payload) return null;
  return {
    situationSummary: payload.situation,
    keyConflicts: payload.disagreements,
    disagreements: payload.disagreements,
    advice: payload.final_advice,
    actionItems: payload.action_items.map((a) => ({
      title: a.title,
      detail: a.detail,
      timing: a.timing,
    })),
    caveats: payload.caveats,
  };
}

export function toSession(res: BackendConsultationResponse): ConsultationSession {
  const r1 = findRound(res.rounds, 'round_1');
  const r2 = findRound(res.rounds, 'round_2');
  const r3 = findRound(res.rounds, 'round_3');

  const rounds: DiscussionRound[] = [];
  const r2msgs = mapDiscussionRound(r2, 'rebuttal');
  if (r2msgs.length > 0) rounds.push({ roundNumber: 1, messages: r2msgs });
  const r3msgs = mapDiscussionRound(r3, 'deepdive');
  if (r3msgs.length > 0) rounds.push({ roundNumber: 2, messages: r3msgs });

  return {
    userInput: res.user_question,
    opinions: mapOpinions(r1),
    rounds,
    finalResult: mapFinal(res.final),
  };
}
