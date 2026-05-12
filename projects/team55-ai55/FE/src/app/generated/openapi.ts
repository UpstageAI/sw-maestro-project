/* Generated from FastAPI OpenAPI schema. Do not edit by hand. */



export const openApiPaths = {
  health: () => "/v1/health",
  createProject: () => "/v1/projects",
  analyze: (project_id: string) => `/v1/projects/${encodeURIComponent(project_id)}/analyze`,
  approveMilestones: (project_id: string) => `/v1/projects/${encodeURIComponent(project_id)}/milestones:approve`,
  suggestMilestones: (project_id: string) => `/v1/projects/${encodeURIComponent(project_id)}/milestones:suggest`,
  simulateRisk: (project_id: string) => `/v1/projects/${encodeURIComponent(project_id)}/risk:simulate`,
  approveSchedule: (project_id: string) => `/v1/projects/${encodeURIComponent(project_id)}/schedule:approve`,
} as const;



export type AgentMeta = {
  "decomposition_calls"?: number;
  "narrator_calls"?: number;
  "schema_retries"?: number;
};

export type AnalyzeMeta = {
  "latency_ms": number;
  "agent_latencies_ms": Record<string, number>;
  "cache_hit": boolean;
  "llm_calls": LlmCalls;
  "llm_fallbacks"?: LlmFallbacks;
};

export type AnalyzeOptions = {
  "request_decomposition_for"?: Array<string>;
  "schedule_horizon_days"?: number;
  "include_unscheduled_in_response"?: boolean;
  "use_llm"?: boolean;
};

export type AnalyzeRequest = {
  "snapshot": ProjectSnapshot;
  "options"?: AnalyzeOptions;
};

export type AnalyzeResponse = {
  "project_id": string;
  "snapshot_hash": string;
  "priority": PriorityResponse;
  "schedule": ScheduleResponse;
  "risk": RiskResponse;
  "meta": AnalyzeMeta;
};

export type ApproveScheduleRequest = {
  "snapshot_hash": string;
  "approvals": Array<ScheduleApproval>;
};

export type ApproveScheduleResponse = {
  "events_created": Array<InternalCalendarEvent>;
  "events_rejected": Array<EventRejected>;
};

export type AvailableHours = {
  "day_of_week": number;
  "start": string;
  "end": string;
};

export type CalendarEventSource = "ai_suggested" | "pm_manual" | "external_blocking";

export type CandidateSlot = {
  "starts_at": string;
  "ends_at": string;
  "time_blocks"?: Array<ScheduleBlock>;
  "quality": SlotQuality;
  "fit_score": number;
  "conflicts": Array<Conflict>;
  "rationale_facts": Array<string>;
};

export type Conflict = {
  "event_id": string;
  "kind": "soft_overlap" | "hard_overlap";
};

export type DefaultWorkingHours = {
  "weekday": HourRange;
  "weekend": HourRange;
};

export type EventRejected = {
  "task_id": string;
  "reason": string;
};

export type HTTPValidationError = {
  "detail"?: Array<ValidationError>;
};

export type HourRange = {
  "start": string;
  "end": string;
  "enabled"?: boolean;
};

export type ImportanceLevel = "low" | "medium" | "high" | "critical";

export type InternalCalendarEvent = {
  "event_id": string;
  "project_id": string;
  "task_id": string;
  "assignee_id"?: string | null;
  "starts_at": string;
  "ends_at": string;
  "approved": boolean;
  "approved_at"?: string | null;
  "source"?: CalendarEventSource;
};

export type LlmCalls = {
  "priority_decompose"?: number;
  "priority_narrate"?: number;
  "schedule_rerank"?: number;
  "risk_soft_checks"?: number;
  "risk_narrate"?: number;
  "total"?: number;
};

export type LlmFallbacks = {
  "schedule_rerank_violation"?: boolean;
  "risk_soft_checks_timeout"?: boolean;
  "narrator_fallback_template"?: boolean;
  "priority_narrator_fallback"?: boolean;
  "risk_narrator_fallback"?: boolean;
};

export type Member = {
  "member_id": string;
  "name": string;
  "role": string;
  "weekly_capacity_hours"?: number;
  "available_hours"?: Array<AvailableHours>;
};

export type MemberWorkload = {
  "member_id": string;
  "scheduled_hours_next_7d": number;
  "capacity_hours": number;
  "utilization": number;
  "is_overloaded": boolean;
};

export type Milestone = {
  "milestone_id": string;
  "project_id": string;
  "name": string;
  "due_date": string;
  "status": MilestoneStatus;
  "ai_rationale"?: string;
  "approved_at"?: string | null;
};

export type MilestoneApproveRequest = {
  "approved": Array<ProposedMilestone>;
  "rejected_count"?: number;
};

export type MilestoneApproveResponse = {
  "milestones": Array<Milestone>;
};

export type MilestoneStatus = "proposed" | "approved" | "archived";

export type MilestoneSuggestRequest = {
  "snapshot": ProjectSnapshot;
  "max_milestones"?: number;
};

export type MilestoneSuggestResponse = {
  "project_id": string;
  "proposed_milestones": Array<ProposedMilestone>;
  "agent_meta": Record<string, number>;
};

export type PriorityFactors = {
  "deadline_pressure": number;
  "importance": number;
  "predecessor_pressure": number;
  "progress_gap": number;
  "overload_penalty": number;
};

export type PriorityResponse = {
  "project_id": string;
  "tasks_priority": Array<PriorityScore>;
  "task_decompositions": Array<TaskDecomposition>;
  "task_assignments": Array<TaskAssignment>;
  "warnings": Array<string>;
  "agent_meta"?: AgentMeta;
};

export type PriorityScore = {
  "task_id": string;
  "score": number;
  "rank": number;
  "factors": PriorityFactors;
  "evidence_facts": Array<string>;
  "rationale": string;
};

export type Project = {
  "project_id": string;
  "name": string;
  "goal"?: string;
  "starts_at": string;
  "ends_at": string;
  "default_working_hours": DefaultWorkingHours;
  "timezone"?: string;
};

export type ProjectCreate = {
  "name": string;
  "goal"?: string;
  "starts_at": string;
  "ends_at": string;
  "default_working_hours": DefaultWorkingHours;
  "timezone"?: string;
};

export type ProjectSnapshot = {
  "project": Project;
  "members": Array<Member>;
  "tasks": Array<Task>;
  "milestones": Array<Milestone>;
  "calendar_events": Array<InternalCalendarEvent>;
};

export type ProposedMilestone = {
  "name": string;
  "due_date": string;
  "ai_rationale"?: string;
};

export type RiskAction = {
  "type": "reschedule" | "reassign" | "split_task" | "raise_importance" | "lower_importance" | "add_predecessor" | "remove_predecessor";
  "target_task_id"?: string | null;
  "from"?: string | null;
  "to"?: string | null;
};

export type RiskCheck = {
  "id": string;
  "group": "deadline" | "dependency" | "workload";
  "label": string;
  "result": "pass" | "fail" | "not_applicable";
  "applicable": boolean;
  "is_blocker": boolean;
  "evidence_facts": Array<string>;
};

export type RiskLevel = "ok" | "watch" | "at_risk" | "overdue";

export type RiskResponse = {
  "project_id": string;
  "checks": Array<RiskCheck>;
  "soft_checks": Array<SoftCheck>;
  "task_risk_levels": Array<TaskRiskLevel>;
  "member_workload": Array<MemberWorkload>;
  "blockers_failed": Array<string>;
  "suggestions": Array<RiskSuggestion>;
  "summary": string;
};

export type RiskSimulateRequest = {
  "snapshot": ProjectSnapshot;
  "applied_suggestion_ids"?: Array<string>;
};

export type RiskSimulateResponse = {
  "project_id": string;
  "applied_suggestion_ids": Array<string>;
  "before": RiskResponse;
  "after": RiskResponse;
  "changed_check_ids": Array<string>;
  "score_action_coherence": ScoreActionCoherence;
};

export type RiskSuggestion = {
  "id": string;
  "fixes_check_ids": Array<string>;
  "action": RiskAction;
  "rationale_facts": Array<string>;
  "removes_blocker": boolean;
  "user_facing_text": string;
};

export type ScheduleApproval = {
  "task_id": string;
  "candidate_slot_index": number;
  "override_starts_at"?: string | null;
  "override_ends_at"?: string | null;
};

export type ScheduleBlock = {
  "starts_at": string;
  "ends_at": string;
};

export type ScheduleResponse = {
  "project_id": string;
  "slot_proposals": Array<SlotProposal>;
  "unschedulable": Array<UnschedulableTask>;
  "warnings": Array<string>;
};

export type ScoreActionCoherence = {
  "priority_delta": number;
  "priority_delta_by_task": Record<string, number>;
  "changed_to_pass_ids": Array<string>;
  "passes_threshold": boolean;
};

export type SlotProposal = {
  "task_id": string;
  "candidate_slots": Array<CandidateSlot>;
  "selected_index": number;
  "rerank_rationale"?: string | null;
  "rerank_source"?: "deterministic" | "llm_reranked";
};

export type SlotQuality = "preferred" | "acceptable" | "fallback";

export type SoftCheck = {
  "id": string;
  "trigger_label": "implicit_dependency_suspected" | "repeated_delay_root_cause" | "milestone_task_mismatch" | "task_definition_too_vague" | "duplicate_task_suspected";
  "confidence": number;
  "involved_task_ids": Array<string>;
  "supporting_facts": Array<string>;
  "suggested_action"?: RiskAction | null;
  "user_facing_text": string;
};

export type Task = {
  "task_id": string;
  "project_id": string;
  "milestone_id"?: string | null;
  "title": string;
  "description"?: string;
  "assignee_id"?: string | null;
  "deadline"?: string | null;
  "importance": ImportanceLevel;
  "estimated_hours"?: number | null;
  "status": TaskStatus;
  "progress_percent"?: number;
  "delay_reason"?: string | null;
  "predecessor_ids"?: Array<string>;
  "created_at"?: string | null;
  "updated_at"?: string | null;
};

export type TaskAssignment = {
  "task_id": string;
  "assignee_id": string;
  "rationale_facts": Array<string>;
  "rationale": string;
};

export type TaskDecomposition = {
  "source_task_id": string;
  "subtasks": Array<TaskDecompositionSubtask>;
  "decomposition_confidence": number;
};

export type TaskDecompositionSubtask = {
  "title": string;
  "description"?: string;
  "estimated_hours_range": [number, number];
  "suggested_assignee_role"?: string | null;
  "suggested_predecessors_within_decomposition"?: Array<number>;
};

export type TaskRiskLevel = {
  "task_id": string;
  "level": RiskLevel;
  "reasons": Array<string>;
};

export type TaskStatus = "todo" | "in_progress" | "blocked" | "review" | "done" | "cancelled";

export type UnschedulableTask = {
  "task_id": string;
  "reasons": Array<"predecessor_incomplete" | "no_capacity_before_deadline" | "estimated_hours_missing" | "assignee_missing" | "deadline_in_past" | "circular_dependency">;
};

export type ValidationError = {
  "loc": Array<string | number>;
  "msg": string;
  "type": string;
  "input"?: unknown;
  "ctx"?: Record<string, unknown>;
};

