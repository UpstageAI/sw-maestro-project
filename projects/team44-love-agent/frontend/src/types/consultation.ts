// 상담 진행 단계 및 메시지 타입 정의
import type { AgentId } from './agent';

export type ConsultationStep =
  | 'input'
  | 'loading'
  | 'opinions'
  | 'discussion'
  | 'result'
  | 'final_advice';

// 슈퍼바이저가 최종 보고를 토대로 4명 중 한 명을 골라 던지는 한 줄 조언.
export type PunchlineVibe = 'harsh' | 'hopeful' | 'chaotic' | 'cold';

export interface Punchline {
  chosenAgentId: string;
  oneLiner: string;
  vibe: PunchlineVibe;
  rationale: string;
}

// 상담 기록 항목 — localStorage에 영속화돼 새 상담을 시작해도 사라지지 않는다.
export interface ConsultationHistoryEntry {
  consultationId: string;
  userInput: string;
  startedAt: string;
  completedAt: string | null;
  status: string;
  session: ConsultationSession;
  punchline: Punchline | null;
}

// 1라운드 stance — 스키마 §2.2
export type StanceType = 'proceed' | 'pause' | 'withdraw' | 'clarify' | 'mixed';

// 2·3라운드 반박/보완 자세 — 스키마 §2.3
export type AgreementType = 'agree' | 'partial' | 'disagree' | 'extend';

// 프론트 표시용 라벨 (반박/심화)
export type MessageType = 'opinion' | 'rebuttal' | 'deepdive';

export const MESSAGE_TYPE_LABEL: Record<MessageType, string> = {
  opinion: '의견',
  rebuttal: '뚜까팸',
  deepdive: '최종 한 방',
};

// 1라운드 에이전트 의견
export interface AgentOpinion {
  agentId: AgentId;
  advice: string;
  rationale: string;
  stance: StanceType;
}

// 토론 발언 한 줄
export interface DiscussionMessage {
  agentId: AgentId;
  content: string;
  messageType?: MessageType;
  replyToAgentId?: AgentId;
}

// 라운드 한 개
export interface DiscussionRound {
  roundNumber: number;
  messages: DiscussionMessage[];
}

// 실행 방안 항목 — 스키마 §5.4.4
export interface ActionItem {
  title: string;
  detail: string;
  timing: 'immediate' | 'short_term' | 'long_term';
}

// 최종 결과 — 스키마 FinalPayload 기반
export interface FinalResult {
  situationSummary: string;
  keyConflicts: string[];
  disagreements?: string[];
  advice: string;
  actionItems: ActionItem[];
  caveats?: string[];
}

// 전체 상담 세션
export interface ConsultationSession {
  userInput: string;
  opinions: AgentOpinion[];
  rounds: DiscussionRound[];
  finalResult: FinalResult | null;
}
