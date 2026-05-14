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

export type KnownHoldReason = 'HOLD_REVIEW_REQUIRED' | 'HOLD_DATA_INSUFFICIENT';

export type HoldReason = KnownHoldReason | (string & {});

export interface ReportCadenceEvent {
  run_id: string;
  event_type: string;
  lifecycle_status: LifecycleStatus;
  created_at: string;
}

export interface AgentRunState {
  run_id: string;
  lifecycle_status: LifecycleStatus;
  hold_reason?: HoldReason;
}
