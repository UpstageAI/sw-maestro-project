/** Area id is now a free string — backend validates against the seed JSON. */
export type Area = string;
export type Category = 'food' | 'place' | 'experience';
export type Language = 'ko' | 'en';

/** Area metadata served by GET /api/areas (data-driven from the seed). */
export interface AreaInfo {
  id: string;
  name_ko: string;
  name_en: string;
  match_ko: string[];
  match_en: string[];
}

export interface Mission {
  id: string;
  title: string;
  hook: string;
  place_id: string;
  place_name: string;
  route_hint: string;
  proof_method: string;
  estimated_minutes: number;
  category: Category;
}

export interface Verdict {
  ok: boolean;
  reason: string;
  comment: string;
}

export interface ContextInput {
  area: Area;
  group: string;
  timeBudget: string;
  mood: string;
  avoid: string;
  language: Language;
}

/* ── Chat ── */

export type ChatRole = 'bot' | 'user';

export type Step =
  | 'greet'
  | 'ask_area'
  | 'ask_group'
  | 'ask_time'
  | 'ask_mood'
  | 'ask_avoid'
  | 'generating'
  | 'show_missions'
  | 'await_photo'
  | 'verifying'
  | 'show_verdict';

export type QuickReplyIntent =
  | 'set_area'
  | 'set_group'
  | 'set_time'
  | 'set_mood'
  | 'set_avoid'
  | 'reroll_all'
  | 'reset'
  | 'restart_after_verdict';

export interface QuickReply {
  label: string;
  intent: QuickReplyIntent;
  emoji?: string;
  payload?: unknown;
}

export type MessageContent =
  | { kind: 'text'; text: string }
  | { kind: 'photo_upload'; mission: Mission; thumbnail?: string }
  | { kind: 'verdict'; mission: Mission; verdict: Verdict; thumbnail?: string };

export interface ChatMessage {
  id: string;
  role: ChatRole;
  ts: number;
  content: MessageContent;
  quickReplies?: QuickReply[];
  consumed?: boolean;
}

/* ── Panel ── */

export type PanelMissionState = 'pool' | 'active' | 'passed' | 'failed' | 'rejected';

export interface PanelMission {
  mission: Mission;
  state: PanelMissionState;
  generatedAt: number;
  pickedAt?: number;
  completedAt?: number;
  verdict?: Verdict;
  thumbnail?: string;
}

/* ── Persistence ── */

export const CHAT_STATE_VERSION = 4;

export interface QuickOption {
  label: string;
  payload: string;
}

export interface ChatState {
  version: number;
  messages: ChatMessage[];
  step: Step;
  context: Partial<ContextInput>;
  selectedMissionId: string | null;
  rejectedPlaceIds: string[];
  panel: PanelMission[];
}
