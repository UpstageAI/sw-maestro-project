import { AnalyzeResult } from "./analysisTypes";
import {
  openApiPaths,
  type AnalyzeResponse as BackendAnalyzeResponse,
  type ApproveScheduleResponse as BackendApproveScheduleResponse,
  type MilestoneApproveResponse as BackendMilestoneApproveResponse,
  type MilestoneSuggestResponse as BackendMilestoneSuggestResponse,
  type ProjectOutput as BackendProject,
  type RiskSimulateResponse as BackendRiskSimulateResponse,
} from "./generated/openapi";
import { CalendarEvent, Project, Task, mintId } from "./store";

type ViteImportMeta = ImportMeta & { env?: { VITE_API_BASE_URL?: string } };

export const API_BASE = (import.meta as ViteImportMeta).env?.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const SEOUL_OFFSET = "+09:00";

export class ApiError extends Error {
  code: string;
  details: unknown;

  constructor(message: string, code: string, details?: unknown) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

const taskInfoFieldMap: Record<string, string> = {
  deadline: "dueDate",
  estimated_hours: "estimatedHours",
  importance: "importance",
  status: "status",
  title: "title",
};

export function taskInfoFieldsFromError(error: unknown): string[] {
  if (!(error instanceof ApiError) || error.code !== "task_info_insufficient") {
    return [];
  }
  const fields = (error.details as { fields?: unknown })?.fields;
  if (!Array.isArray(fields)) {
    return [];
  }
  return fields
    .filter((field): field is string => typeof field === "string")
    .map((field) => taskInfoFieldMap[field] ?? field)
    .filter((field, index, all) => all.indexOf(field) === index);
}

export function userFacingApiError(error: unknown, fallback = "API 요청이 실패했습니다.") {
  if (error instanceof ApiError) {
    if (error.code === "rate_limited") return "잠시 후 다시 시도해 주세요.";
    if (error.code === "agent_failed") return "AI 분석 일부가 실패했습니다. 다시 시도해 주세요.";
    if (error.code === "network_error") return "네트워크 오류입니다. 마지막 분석 결과를 표시 중입니다.";
    if (error.code === "snapshot_hash_stale") return "데이터가 변경되어 분석을 다시 실행합니다.";
    if (error.code === "circular_dependency") {
      const cyclePath = (error.details as { cycle_path?: unknown })?.cycle_path;
      const path = Array.isArray(cyclePath) ? cyclePath.filter((item): item is string => typeof item === "string").join(" → ") : "";
      return `순환 의존이 있습니다${path ? `: ${path}` : ""}`;
    }
    return error.message || fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

export function localProjectFingerprint(project: Project) {
  return JSON.stringify({
    project: {
      id: project.id,
      name: project.name,
      goal: project.goal,
      startsAt: project.startsAt,
      endsAt: project.endsAt,
      baseHours: project.baseHours,
      defaultWorkStart: project.defaultWorkStart ?? "09:00",
      defaultWorkEnd: project.defaultWorkEnd ?? "18:00",
      weekendEnabled: project.weekendEnabled ?? false,
      weekendWorkStart: project.weekendWorkStart ?? "10:00",
      weekendWorkEnd: project.weekendWorkEnd ?? "16:00",
    },
    members: project.members,
    milestones: project.milestones,
    tasks: project.tasks.map(taskForFingerprint),
    events: project.events,
  });
}

export function isProjectAnalysisStale(project: Project, analysisFingerprint: string) {
  return localProjectFingerprint(project) !== analysisFingerprint;
}

export async function createProject(project: Project) {
  const body = await apiRequest<BackendProject>(openApiPaths.createProject(), {
    method: "POST",
    body: JSON.stringify({
      name: project.name,
      goal: project.goal,
      starts_at: project.startsAt,
      ends_at: project.endsAt,
      default_working_hours: {
        weekday: { start: project.defaultWorkStart ?? "09:00", end: project.defaultWorkEnd ?? "18:00", enabled: true },
        weekend: {
          start: project.weekendWorkStart ?? "10:00",
          end: project.weekendWorkEnd ?? "16:00",
          enabled: project.weekendEnabled ?? false,
        },
      },
      timezone: "Asia/Seoul",
    }),
  });
  return body.project_id;
}

export async function suggestMilestones(project: Project) {
  const body = await apiRequest<BackendMilestoneSuggestResponse>(openApiPaths.suggestMilestones(project.id), {
    method: "POST",
    body: JSON.stringify({ snapshot: buildSnapshotForApi(project), max_milestones: 8 }),
  });
  return body.proposed_milestones.map((item) => ({
    id: mintId("ms"),
    title: item.name,
    dueDate: item.due_date,
    status: "pending" as const,
    aiRationale: item.ai_rationale,
  }));
}

export async function approveMilestones(project: Project) {
  const body = await apiRequest<BackendMilestoneApproveResponse>(openApiPaths.approveMilestones(project.id), {
    method: "POST",
    body: JSON.stringify({
      approved: project.milestones
        .filter((milestone) => milestone.status !== "archived")
        .map((milestone) => ({
          name: milestone.title,
          due_date: milestone.dueDate,
          ai_rationale: milestone.aiRationale ?? "",
        })),
      rejected_count: project.milestones.filter((milestone) => milestone.status === "archived").length,
    }),
  });
  return body.milestones.map((item) => ({
    id: item.milestone_id,
    title: item.name,
    dueDate: item.due_date,
    status: "approved" as const,
    aiRationale: item.ai_rationale,
  }));
}

export async function analyzeProject(project: Project, requestDecompositionFor: string[] = []): Promise<AnalyzeResult> {
  const body = await apiRequest<BackendAnalyzeResponse>(openApiPaths.analyze(project.id), {
    method: "POST",
    body: JSON.stringify({
      snapshot: buildSnapshotForApi(project),
      options: {
        request_decomposition_for: requestDecompositionFor,
        schedule_horizon_days: 14,
        include_unscheduled_in_response: true,
      },
    }),
  });
  return mapAnalyze(project, body);
}

export function applyPriorityResultsToTasks(project: Project, result: Pick<AnalyzeResult, "priority" | "taskAssignments">): Project {
  if (result.priority.length === 0 && result.taskAssignments.length === 0) return project;
  const assignmentByTask = new Map(result.taskAssignments.map((item) => [item.taskId, item.assigneeId]));
  const priorityByTask = new Map(result.priority.map((item) => [item.taskId, item]));
  const priorityUpdatedAt = new Date().toISOString();

  return {
    ...project,
    tasks: project.tasks.map((task) => {
      const assigneeId = assignmentByTask.get(task.id);
      const priority = priorityByTask.get(task.id);
      if (!assigneeId && !priority) return task;
      const shouldApplyAssignee = task.assigneeId == null && isPriorityAssignableStatus(task.status) && Boolean(assigneeId);

      return {
        ...task,
        assigneeId: shouldApplyAssignee ? assigneeId : task.assigneeId,
        ...(priority
          ? {
              priorityScore: priority.score,
              priorityRank: priority.rank,
              priorityFactors: { ...priority.factors },
              priorityEvidenceFacts: [...priority.evidenceFacts],
              priorityRationale: priority.rationale,
              priorityUpdatedAt,
            }
          : {}),
      };
    }),
  };
}

export function applyPriorityAssignments(project: Project, result: Pick<AnalyzeResult, "taskAssignments">): Project {
  return applyPriorityResultsToTasks(project, { ...result, priority: [] });
}

export async function approveProjectSchedule(
  project: Project,
  result: AnalyzeResult,
  selectedTaskIds: string[],
  analysisFingerprint?: string,
) {
  if (analysisFingerprint && isProjectAnalysisStale(project, analysisFingerprint)) {
    throw new ApiError("데이터가 변경되어 분석을 다시 실행합니다.", "snapshot_hash_stale");
  }
  const body = await apiRequest<BackendApproveScheduleResponse>(openApiPaths.approveSchedule(project.id), {
    method: "POST",
    body: JSON.stringify({
      snapshot_hash: result.snapshotHash,
      approvals: result.schedule.proposals
        .filter((proposal) => selectedTaskIds.includes(proposal.taskId))
        .map((proposal) => {
          const approval: {
            task_id: string;
            candidate_slot_index: number;
            override_starts_at?: string;
            override_ends_at?: string;
          } = { task_id: proposal.taskId, candidate_slot_index: proposal.selectedIndex };
          if (proposal.overrideDate && proposal.overrideStartTime && proposal.overrideEndTime) {
            approval.override_starts_at = `${proposal.overrideDate}T${proposal.overrideStartTime}:00${SEOUL_OFFSET}`;
            approval.override_ends_at = `${proposal.overrideDate}T${proposal.overrideEndTime}:00${SEOUL_OFFSET}`;
          }
          return approval;
        }),
    }),
  });

  const created = body.events_created.map((event): CalendarEvent => {
    const task = project.tasks.find((item) => item.id === event.task_id);
    return {
      id: event.event_id,
      taskId: event.task_id,
      title: task?.title ?? "Untitled task",
      date: toDateInput(event.starts_at),
      assigneeId: event.assignee_id ?? null,
      startTime: toTimeInput(event.starts_at),
      endTime: toTimeInput(event.ends_at),
      approved: event.approved,
      source: event.source ?? "ai_suggested",
    };
  });

  return {
    project: {
      ...project,
      events: [...project.events, ...created],
      lastSnapshotHash: result.snapshotHash,
    },
    rejected: body.events_rejected,
  };
}

export type RiskSimulationResult = BackendRiskSimulateResponse;

export async function simulateRiskSuggestion(project: Project, suggestionId: string) {
  return apiRequest<BackendRiskSimulateResponse>(openApiPaths.simulateRisk(project.id), {
    method: "POST",
    body: JSON.stringify({
      snapshot: buildSnapshotForApi(project),
      applied_suggestion_ids: [suggestionId],
    }),
  });
}

async function apiRequest<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    });
  } catch (error) {
    throw new ApiError(error instanceof Error ? error.message : "Network error", "network_error");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = body.error ?? {};
    throw new ApiError(error.message ?? "API 요청이 실패했습니다.", error.code ?? "api_error", error.details);
  }
  return body as T;
}

export function buildSnapshotForApi(project: Project) {
  return {
    project: {
      project_id: project.id,
      name: project.name,
      goal: project.goal,
      starts_at: project.startsAt,
      ends_at: project.endsAt,
      default_working_hours: {
        weekday: { start: project.defaultWorkStart ?? "09:00", end: project.defaultWorkEnd ?? "18:00", enabled: true },
        weekend: {
          start: project.weekendWorkStart ?? "10:00",
          end: project.weekendWorkEnd ?? "16:00",
          enabled: project.weekendEnabled ?? false,
        },
      },
      timezone: "Asia/Seoul",
    },
    members: project.members.map((member) => ({
      member_id: member.id,
      name: member.name,
      role: member.role,
      weekly_capacity_hours: member.availableHours ?? project.baseHours,
      available_hours: [0, 1, 2, 3, 4].map((day) => ({
        day_of_week: day,
        start: member.workStart,
        end: member.workEnd,
      })),
    })),
    milestones: project.milestones
      .filter((milestone) => milestone.status !== "pending")
      .map((milestone) => ({
        milestone_id: milestone.id,
        project_id: project.id,
        name: milestone.title,
        due_date: milestone.dueDate,
        status: milestone.status === "approved" ? "approved" : "archived",
        ai_rationale: milestone.aiRationale ?? "",
        approved_at: milestone.status === "approved" ? `${milestone.dueDate}T09:00:00${SEOUL_OFFSET}` : null,
      })),
    tasks: project.tasks.map((task) => ({
      task_id: task.id,
      project_id: project.id,
      milestone_id: task.milestoneId ?? null,
      title: task.title,
      description: task.description,
      assignee_id: task.assigneeId ?? null,
      deadline: task.dueDate ? `${task.dueDate}T18:00:00${SEOUL_OFFSET}` : null,
      importance: task.importance,
      estimated_hours: task.estimatedHours ?? null,
      status: task.status,
      progress_percent: task.progress,
      delay_reason: task.delayReason ?? null,
      predecessor_ids: task.predecessorIds,
      created_at: `${project.startsAt}T09:00:00${SEOUL_OFFSET}`,
      updated_at: `${project.startsAt}T09:00:00${SEOUL_OFFSET}`,
    })),
    calendar_events: project.events.map((event) => ({
      event_id: event.id,
      project_id: project.id,
      task_id: event.taskId,
      assignee_id: event.assigneeId,
      starts_at: `${event.date}T${event.startTime}:00${SEOUL_OFFSET}`,
      ends_at: `${event.date}T${event.endTime}:00${SEOUL_OFFSET}`,
      approved: event.approved,
      approved_at: event.approved ? `${event.date}T${event.endTime}:00${SEOUL_OFFSET}` : null,
      source: event.source,
    })),
  };
}

export function mapAnalyze(project: Project, body: BackendAnalyzeResponse): AnalyzeResult {
  const taskRiskLevels = Object.fromEntries(
    body.risk.task_risk_levels.map((item) => [item.task_id, item.level]),
  ) as AnalyzeResult["risk"]["taskRiskLevels"];

  return {
    snapshotHash: body.snapshot_hash,
    meta: {
      llmFallbacks: {
        scheduleRerankViolation: Boolean(body.meta?.llm_fallbacks?.schedule_rerank_violation),
        riskSoftChecksTimeout: Boolean(body.meta?.llm_fallbacks?.risk_soft_checks_timeout),
        narratorFallbackTemplate: Boolean(body.meta?.llm_fallbacks?.narrator_fallback_template),
        priorityNarratorFallback: Boolean(body.meta?.llm_fallbacks?.priority_narrator_fallback),
        riskNarratorFallback: Boolean(body.meta?.llm_fallbacks?.risk_narrator_fallback),
      },
    },
    priority: body.priority.tasks_priority.map((item) => ({
      taskId: item.task_id,
      rank: item.rank,
      score: item.score,
      factors: {
        deadline: item.factors.deadline_pressure,
        importance: item.factors.importance,
        predecessor: item.factors.predecessor_pressure,
        progress: item.factors.progress_gap,
        overload: item.factors.overload_penalty,
      },
      evidenceFacts: item.evidence_facts,
      rationale: item.rationale,
    })),
    taskAssignments: (body.priority.task_assignments ?? []).map((item) => ({
      taskId: item.task_id,
      assigneeId: item.assignee_id,
      rationaleFacts: item.rationale_facts,
      rationale: item.rationale,
    })),
    decompositions: body.priority.task_decompositions.map((item) => ({
      sourceTaskId: item.source_task_id,
      confidence: item.decomposition_confidence,
      subtasks: item.subtasks,
    })),
    schedule: {
      proposals: body.schedule.slot_proposals.map((proposal) => ({
        taskId: proposal.task_id,
        selectedIndex: proposal.selected_index,
        candidateSlots: proposal.candidate_slots.map((slot) => {
          return {
            date: toDateInput(slot.starts_at),
            startTime: toTimeInput(slot.starts_at),
            endTime: toTimeInput(slot.ends_at),
            timeBlocks: (slot.time_blocks && slot.time_blocks.length > 0 ? slot.time_blocks : [{ starts_at: slot.starts_at, ends_at: slot.ends_at }]).map((block) => ({
              date: toDateInput(block.starts_at),
              startTime: toTimeInput(block.starts_at),
              endTime: toTimeInput(block.ends_at),
            })),
            quality: slot.quality,
            fitScore: slot.fit_score,
            conflicts: slot.conflicts.map((conflict) => `${conflict.kind}:${conflict.event_id}`),
            rerankSource: proposal.rerank_source ?? "deterministic",
            rerankRationale: proposal.rerank_rationale ?? undefined,
          };
        }),
      })),
      unschedulable: body.schedule.unschedulable.map((item) => ({
        taskId: item.task_id,
        reason: item.reasons.join(", "),
      })),
    },
    risk: {
      summary: body.risk.summary,
      blockersFailed: body.risk.blockers_failed,
      checks: body.risk.checks.map((check) => ({
        id: check.id,
        group: check.group,
        label: check.label,
        status: check.result,
        blocker: check.is_blocker,
        evidenceFacts: check.evidence_facts,
      })),
      taskRiskLevels,
      suggestions: body.risk.suggestions.map((suggestion) => {
        const taskId = suggestion.action.target_task_id ?? project.tasks[0]?.id ?? "";
        const sourceMemberId = suggestion.action.type === "reassign" ? suggestion.action.from ?? undefined : undefined;
        const targetMemberId = suggestion.action.type === "reassign" ? suggestion.action.to ?? undefined : undefined;
        const sourceMember = project.members.find((member) => member.id === sourceMemberId);
        const targetMember = project.members.find((member) => member.id === targetMemberId);
        return {
	          id: suggestion.id,
          fixesCheckIds: suggestion.fixes_check_ids,
	          taskId,
	          action: suggestion.action.type,
	          summary: suggestion.user_facing_text,
          rationaleFacts: suggestion.rationale_facts,
          sourceMemberId,
          sourceMemberName: sourceMember?.name,
          targetMemberId,
          targetMemberName: targetMember?.name,
          patch: patchForAction(project, taskId, suggestion.action),
        };
      }),
      softChecks: body.risk.soft_checks.map((check) => ({
        id: check.id,
        triggerLabel: check.trigger_label,
        confidence: check.confidence,
        involvedTaskIds: check.involved_task_ids,
        supportingFacts: check.supporting_facts,
        userFacingText: check.user_facing_text,
        taskId: check.suggested_action?.target_task_id ?? check.involved_task_ids[0] ?? "",
        patch: check.suggested_action
          ? patchForAction(project, check.suggested_action.target_task_id ?? check.involved_task_ids[0] ?? "", check.suggested_action)
          : {},
      })),
      memberWorkload: body.risk.member_workload.map((item) => ({
        memberId: item.member_id,
        assignedHours: item.scheduled_hours_next_7d,
        utilization: item.utilization,
      })),
    },
  };
}

export function patchForAction(project: Project, taskId: string, action: { type: string; to?: string | null }) {
  const task = project.tasks.find((item) => item.id === taskId);
  if (!task) return {};
  if (action.type === "reassign") return { assigneeId: action.to ?? null };
  if (action.type === "reschedule" && action.to && /^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(action.to)) {
    return { dueDate: action.to.slice(0, 10) };
  }
  if (action.type === "raise_importance") return { importance: "critical" as const };
  if (action.type === "lower_importance") return { importance: "medium" as const };
  if (action.type === "add_predecessor" && action.to) {
    return { predecessorIds: [...new Set([...task.predecessorIds, action.to])] };
  }
  if (action.type === "remove_predecessor" && action.to) {
    return { predecessorIds: task.predecessorIds.filter((id) => id !== action.to) };
  }
  return {};
}

function toDateInput(value: string) {
  return value.slice(0, 10);
}

function toTimeInput(value: string) {
  return value.slice(11, 16);
}

function taskForFingerprint(task: Task) {
  return {
    id: task.id,
    milestoneId: task.milestoneId,
    title: task.title,
    description: task.description,
    assigneeId: task.assigneeId,
    importance: task.importance,
    status: task.status,
    progress: task.progress,
    estimatedHours: task.estimatedHours,
    dueDate: task.dueDate,
    predecessorIds: task.predecessorIds,
    delayReason: task.delayReason,
  };
}

function isPriorityAssignableStatus(status: Task["status"]) {
  return status === "todo" || status === "in_progress";
}
