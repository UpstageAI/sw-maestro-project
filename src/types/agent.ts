export type LifecycleStatus =
  | 'RECEIVED'
  | 'NORMALIZING'
  | 'NEEDS_INPUT'
  | 'RISK_REVIEW'
  | 'HOLD'
  | 'READY_FOR_BE'
  | 'BE_REJECTED'
  | 'EXECUTING'
  | 'RESULT_VERIFYING'
  | 'REPORT_READY'
  | 'NO_ORDER'
  | 'FAILED';

export type HoldReason = 'HOLD_REVIEW_REQUIRED' | 'HOLD_DATA_INSUFFICIENT';

export type GateDecisionType = 'PASS' | 'REJECT' | 'HOLD';

export type FinalAction =
  | 'READY_FOR_BE'
  | 'NO_ORDER'
  | 'HOLD'
  | 'REPORT_READY'
  | 'BE_REJECTED'
  | 'FAILED';

export interface AgentDecisionTrace {
  reason_codes: string[];
  evidence_refs?: string[];
  final_action: FinalAction;
  notes?: string;
}

export interface VerificationResult {
  name: string;
  result: 'pass' | 'fail';
  evidence_refs: string[];
}

export interface GateDecision {
  decision: GateDecisionType;
  reason_codes: string[];
  stage: string;
}

export interface DecisionTrace {
  policy?: AgentDecisionTrace;
  risk?: AgentDecisionTrace;
  evaluator?: AgentDecisionTrace;
  execution?: AgentDecisionTrace;
  run_summary?: {
    final_action: FinalAction;
    be_override: boolean;
  };
}

export interface ReportPayload {
  run_id: string;
  gate_decision: GateDecisionType;
  final_action: FinalAction;
  decision_trace: DecisionTrace;
  user_summary: string;
}

export interface ReportCadenceEvent {
  run_id: string;
  event_type: string;
  lifecycle_status: LifecycleStatus;
  created_at: string;
}

export interface HoldDecision {
  decision: 'HOLD';
  hold_reason: HoldReason;
  reason_codes: string[];
  resume_required: boolean;
}

export interface AgentRunState {
  run_id: string;
  lifecycle_status: LifecycleStatus;
  request_type: string;
  final_action: FinalAction;
  hold_reason?: HoldReason;
}
