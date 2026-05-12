import { RiskLevel, SlotQuality, Task } from "./store";

type FactorKey = "deadline" | "importance" | "predecessor" | "progress" | "overload";

export type PriorityItem = {
  taskId: string;
  rank: number;
  score: number;
  factors: Record<FactorKey, number>;
  evidenceFacts: string[];
  rationale: string;
};

export type TaskAssignment = {
  taskId: string;
  assigneeId: string;
  rationaleFacts: string[];
  rationale: string;
};

export type SlotProposal = {
  taskId: string;
  selectedIndex: number;
  overrideDate?: string;
  overrideStartTime?: string;
  overrideEndTime?: string;
  candidateSlots: Array<{
    date: string;
    startTime: string;
    endTime: string;
    timeBlocks: Array<{
      date: string;
      startTime: string;
      endTime: string;
    }>;
    quality: SlotQuality;
    fitScore: number;
    conflicts: string[];
    rerankSource: "llm_reranked" | "deterministic";
    rerankRationale?: string;
  }>;
};

export type RiskCheck = {
  id: string;
  group: "deadline" | "dependency" | "workload";
  label: string;
  status: "pass" | "fail" | "not_applicable";
  blocker: boolean;
  evidenceFacts: string[];
};

export type RiskSuggestion = {
  id: string;
  fixesCheckIds: string[];
  taskId: string;
  action: "reschedule" | "reassign" | "split_task" | "raise_importance" | "lower_importance" | "add_predecessor" | "remove_predecessor";
  summary: string;
  rationaleFacts: string[];
  sourceMemberId?: string;
  sourceMemberName?: string;
  targetMemberId?: string;
  targetMemberName?: string;
  patch: Partial<Task>;
};

export type AnalyzeResult = {
  snapshotHash: string;
  meta: {
    llmFallbacks: {
      scheduleRerankViolation: boolean;
      riskSoftChecksTimeout: boolean;
      narratorFallbackTemplate: boolean;
      priorityNarratorFallback: boolean;
      riskNarratorFallback: boolean;
    };
  };
  priority: PriorityItem[];
  taskAssignments: TaskAssignment[];
  decompositions: Array<{
    sourceTaskId: string;
    confidence: number;
    subtasks: Array<{
      title: string;
      description?: string;
      estimated_hours_range: [number, number];
    }>;
  }>;
  schedule: {
    proposals: SlotProposal[];
    unschedulable: Array<{ taskId: string; reason: string }>;
  };
  risk: {
    summary: string;
    blockersFailed: string[];
    checks: RiskCheck[];
    taskRiskLevels: Record<string, RiskLevel>;
    suggestions: RiskSuggestion[];
    softChecks: Array<{
      id: string;
      triggerLabel: string;
      confidence: number;
      involvedTaskIds: string[];
      supportingFacts: string[];
      userFacingText: string;
      taskId: string;
      patch: Partial<Task>;
    }>;
    memberWorkload: Array<{ memberId: string; assignedHours: number; utilization: number }>;
  };
};
