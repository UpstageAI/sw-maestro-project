import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import type { AnalyzeResult } from "./analysisTypes";
import { localStoreEnvelopeSchema } from "./schemas";

const STORAGE_KEY = "omc-pm-55:v1";
export const MAX_EXPORT_BYTES = 3 * 1024 * 1024;
export const LOCAL_DATA_NOTICE =
  "이 프로젝트 데이터는 현재 브라우저 localStorage에만 저장됩니다. 브라우저 데이터를 삭제하면 복구할 수 없으니 Export로 정기 백업하세요.";
const ID_PATTERNS = {
  evt: /^evt_[A-Za-z0-9]{8,}$/,
  mem: /^mem_[A-Za-z0-9]{6,}$/,
  ms: /^ms_[A-Za-z0-9]{6,}$/,
  proj: /^proj_[A-Za-z0-9]{8,}$/,
  task: /^task_[A-Za-z0-9]{8,}$/,
};

export type TaskStatus = "todo" | "in_progress" | "blocked" | "review" | "done" | "cancelled";
export type ImportanceLevel = "low" | "medium" | "high" | "critical";
export type RiskLevel = "ok" | "watch" | "at_risk" | "overdue";
export type SlotQuality = "preferred" | "acceptable" | "fallback";

export type Member = {
  id: string;
  name: string;
  role: string;
  availableHours: number;
  workStart: string;
  workEnd: string;
};

export type Milestone = {
  id: string;
  title: string;
  dueDate: string;
  status: "pending" | "approved" | "archived";
  aiRationale?: string;
};

export type Task = {
  id: string;
  milestoneId?: string | null;
  title: string;
  description: string;
  assigneeId?: string | null;
  importance: ImportanceLevel;
  status: TaskStatus;
  progress: number;
  estimatedHours?: number | null;
  dueDate?: string | null;
  predecessorIds: string[];
  delayReason?: string | null;
  priorityScore?: number | null;
  priorityRank?: number | null;
  priorityFactors?: {
    deadline: number;
    importance: number;
    predecessor: number;
    progress: number;
    overload: number;
  } | null;
  priorityEvidenceFacts?: string[];
  priorityRationale?: string | null;
  priorityUpdatedAt?: string | null;
};

export type CalendarEvent = {
  id: string;
  taskId: string;
  title: string;
  date: string;
  assigneeId: string | null;
  startTime: string;
  endTime: string;
  approved: boolean;
  source: "ai_suggested" | "pm_manual" | "external_blocking";
};

export type AnalyzeLatencyEvent = {
  projectId: string;
  latencyMs: number;
  recordedAt: string;
};

export type SuggestionAcceptanceEvent = {
  projectId: string;
  totalSuggestions: number;
  acceptedSuggestions: number;
  recordedAt: string;
};

export type ClientMetrics = {
  analyzeLatenciesMs: AnalyzeLatencyEvent[];
  suggestionAcceptanceEvents: SuggestionAcceptanceEvent[];
};

export type ClientMetricsSummary = {
  analyzeP95Ms: number | null;
  suggestionAcceptanceRate: number | null;
  analyzedSamples: number;
  suggestionEvents: number;
};

export type Project = {
  id: string;
  name: string;
  goal: string;
  startsAt: string;
  endsAt: string;
  baseHours: number;
  defaultWorkStart?: string;
  defaultWorkEnd?: string;
  weekendEnabled?: boolean;
  weekendWorkStart?: string;
  weekendWorkEnd?: string;
  members: Member[];
  milestones: Milestone[];
  tasks: Task[];
  events: CalendarEvent[];
  lastSnapshotHash?: string;
  lastAnalysis?: AnalyzeResult;
  lastAnalysisFingerprint?: string;
};

export type PersistedStore = {
  schemaVersion: 1;
  currentUser: { name: string } | null;
  projects: Project[];
  clientMetrics: ClientMetrics;
};

type AppContextType = PersistedStore & {
  addProject: (project: Project) => void;
  updateProject: (id: string, project: Project) => void;
  replaceStore: (next: PersistedStore) => void;
  exportJson: () => string;
  recordAnalyzeLatency: (projectId: string, latencyMs: number) => void;
  recordSuggestionAcceptance: (projectId: string, totalSuggestions: number, acceptedSuggestions: number) => void;
  login: (name: string) => void;
  logout: () => void;
};

const initialStore: PersistedStore = {
  schemaVersion: 1,
  currentUser: null,
  projects: [],
  clientMetrics: { analyzeLatenciesMs: [], suggestionAcceptanceEvents: [] },
};

const AppContext = createContext<AppContextType | undefined>(undefined);

function normalizeTask(task: Partial<Task> & { id: string; title: string }): Task {
  return {
    description: task.description ?? "",
    status: normalizeStatus(task.status),
    progress: Math.max(0, Math.min(100, task.progress ?? 0)),
    importance: task.importance ?? "medium",
    estimatedHours: task.estimatedHours ?? 4,
    milestoneId: task.milestoneId ?? null,
    assigneeId: task.assigneeId ?? null,
    dueDate: task.dueDate ?? null,
    predecessorIds: task.predecessorIds ?? [],
    delayReason: task.delayReason ?? null,
    priorityScore: task.priorityScore ?? null,
    priorityRank: task.priorityRank ?? null,
    priorityFactors: task.priorityFactors ?? null,
    priorityEvidenceFacts: task.priorityEvidenceFacts ?? [],
    priorityRationale: task.priorityRationale ?? null,
    priorityUpdatedAt: task.priorityUpdatedAt ?? null,
    id: task.id,
    title: task.title,
  };
}

function normalizeStatus(status: unknown): TaskStatus {
  if (status === "in-progress") return "in_progress";
  if (
    status === "todo" ||
    status === "in_progress" ||
    status === "blocked" ||
    status === "review" ||
    status === "done" ||
    status === "cancelled"
  ) {
    return status;
  }
  return "todo";
}

function normalizeProject(project: Project): Project {
  const today = new Date().toISOString().split("T")[0];
  const endsAt = new Date();
  endsAt.setDate(endsAt.getDate() + 28);
  const lastAnalysis = isAnalyzeResultLike(project.lastAnalysis) ? project.lastAnalysis : undefined;
  return {
    ...project,
    startsAt: project.startsAt ?? today,
    endsAt: project.endsAt ?? endsAt.toISOString().split("T")[0],
    baseHours: project.baseHours ?? 40,
    defaultWorkStart: project.defaultWorkStart ?? "09:00",
    defaultWorkEnd: project.defaultWorkEnd ?? "18:00",
    weekendEnabled: project.weekendEnabled ?? false,
    weekendWorkStart: project.weekendWorkStart ?? "10:00",
    weekendWorkEnd: project.weekendWorkEnd ?? "16:00",
    members: (project.members ?? []).map((member) => ({
      ...member,
      availableHours: member.availableHours ?? project.baseHours ?? 40,
      workStart: member.workStart ?? "09:00",
      workEnd: member.workEnd ?? "18:00",
    })),
    milestones: (project.milestones ?? []).map((milestone) => ({
      ...milestone,
      status: milestone.status ?? "pending",
    })),
    tasks: (project.tasks ?? []).map(normalizeTask),
    events: (project.events ?? []).map((event) => ({
      ...event,
      approved: event.approved ?? true,
      source: event.source ?? "ai_suggested",
    })),
    lastAnalysis,
    lastAnalysisFingerprint: lastAnalysis ? project.lastAnalysisFingerprint : undefined,
  };
}

function isAnalyzeResultLike(value: unknown): value is AnalyzeResult {
  const candidate = value as Partial<AnalyzeResult> | undefined;
  return Boolean(
    candidate &&
      typeof candidate.snapshotHash === "string" &&
      candidate.meta &&
      Array.isArray(candidate.priority) &&
      Array.isArray(candidate.taskAssignments) &&
      candidate.schedule &&
      Array.isArray(candidate.schedule.proposals) &&
      Array.isArray(candidate.schedule.unschedulable) &&
      candidate.risk &&
      Array.isArray(candidate.risk.checks),
  );
}

function normalizeClientMetrics(metrics?: Partial<ClientMetrics>): ClientMetrics {
  return {
    analyzeLatenciesMs: (metrics?.analyzeLatenciesMs ?? [])
      .filter((event) => event.projectId && Number.isFinite(event.latencyMs))
      .slice(-200),
    suggestionAcceptanceEvents: (metrics?.suggestionAcceptanceEvents ?? [])
      .filter(
        (event) =>
          event.projectId &&
          Number.isFinite(event.totalSuggestions) &&
          Number.isFinite(event.acceptedSuggestions) &&
          event.totalSuggestions >= 0 &&
          event.acceptedSuggestions >= 0,
      )
      .slice(-200),
  };
}

export function summarizeClientMetrics(metrics: ClientMetrics): ClientMetricsSummary {
  const sortedLatencies = metrics.analyzeLatenciesMs
    .map((event) => event.latencyMs)
    .filter((latency) => Number.isFinite(latency) && latency >= 0)
    .sort((a, b) => a - b);
  const p95Index = sortedLatencies.length === 0 ? -1 : Math.ceil(sortedLatencies.length * 0.95) - 1;
  const totalSuggestions = metrics.suggestionAcceptanceEvents.reduce((sum, event) => sum + event.totalSuggestions, 0);
  const acceptedSuggestions = metrics.suggestionAcceptanceEvents.reduce((sum, event) => sum + event.acceptedSuggestions, 0);
  return {
    analyzeP95Ms: p95Index >= 0 ? sortedLatencies[p95Index] : null,
    suggestionAcceptanceRate: totalSuggestions > 0 ? acceptedSuggestions / totalSuggestions : null,
    analyzedSamples: sortedLatencies.length,
    suggestionEvents: metrics.suggestionAcceptanceEvents.length,
  };
}

function readStore(): PersistedStore {
  if (typeof window === "undefined") return initialStore;

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return initialStore;
    const parsed = JSON.parse(raw) as PersistedStore;
    return {
      schemaVersion: 1,
      currentUser: parsed.currentUser ?? null,
      projects: (parsed.projects ?? []).map(normalizeProject),
      clientMetrics: normalizeClientMetrics(parsed.clientMetrics),
    };
  } catch {
    return initialStore;
  }
}

export function parseExportPayload(text: string, byteSize = new Blob([text]).size): PersistedStore {
  if (byteSize > MAX_EXPORT_BYTES) {
    throw new Error("Import 파일은 3MB 이하만 사용할 수 있습니다.");
  }
  const parsed = localStoreEnvelopeSchema.safeParse(JSON.parse(text));
  if (!parsed.success) {
    throw new Error("지원하지 않는 export 파일입니다.");
  }
  return {
    schemaVersion: 1,
    currentUser: parsed.data.currentUser ?? null,
    projects: (parsed.data.projects as Project[]).map((project) => {
      validateImportedProjectIds(project);
      return normalizeProject(project);
    }),
    clientMetrics: normalizeClientMetrics(parsed.data.clientMetrics),
  };
}

function validateImportedProjectIds(project: Project): void {
  const invalid =
    !ID_PATTERNS.proj.test(project.id) ||
    (project.members ?? []).some((member) => !ID_PATTERNS.mem.test(member.id)) ||
    (project.milestones ?? []).some((milestone) => !ID_PATTERNS.ms.test(milestone.id)) ||
    (project.tasks ?? []).some((task) => !ID_PATTERNS.task.test(task.id)) ||
    (project.events ?? []).some((event) => !ID_PATTERNS.evt.test(event.id));
  if (invalid) {
    throw new Error("백엔드 계약에 맞지 않는 ID가 포함된 export 파일입니다.");
  }
}

export function mintId(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [store, setStore] = useState<PersistedStore>(readStore);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  }, [store]);

  const value = useMemo<AppContextType>(() => {
    const replaceStore = (next: PersistedStore) => {
      setStore({
        schemaVersion: 1,
        currentUser: next.currentUser ?? null,
        projects: (next.projects ?? []).map(normalizeProject),
        clientMetrics: normalizeClientMetrics(next.clientMetrics),
      });
    };

    return {
      ...store,
      addProject: (project) =>
        setStore((prev) => ({
          ...prev,
          projects: [...prev.projects, normalizeProject(project)],
        })),
      updateProject: (id, updated) =>
        setStore((prev) => ({
          ...prev,
          projects: prev.projects.map((project) => (project.id === id ? normalizeProject(updated) : project)),
        })),
      replaceStore,
      exportJson: () => JSON.stringify(store, null, 2),
      recordAnalyzeLatency: (projectId, latencyMs) =>
        setStore((prev) => ({
          ...prev,
          clientMetrics: normalizeClientMetrics({
            ...prev.clientMetrics,
            analyzeLatenciesMs: [
              ...prev.clientMetrics.analyzeLatenciesMs,
              { projectId, latencyMs: Math.round(latencyMs), recordedAt: new Date().toISOString() },
            ],
          }),
        })),
      recordSuggestionAcceptance: (projectId, totalSuggestions, acceptedSuggestions) =>
        setStore((prev) => ({
          ...prev,
          clientMetrics: normalizeClientMetrics({
            ...prev.clientMetrics,
            suggestionAcceptanceEvents: [
              ...prev.clientMetrics.suggestionAcceptanceEvents,
              {
                projectId,
                totalSuggestions,
                acceptedSuggestions,
                recordedAt: new Date().toISOString(),
              },
            ],
          }),
        })),
      login: (name) => setStore((prev) => ({ ...prev, currentUser: { name } })),
      logout: () => setStore((prev) => ({ ...prev, currentUser: null })),
    };
  }, [store]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppStore() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useAppStore must be used within AppProvider");
  return context;
}
