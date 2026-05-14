import { type DragEvent, type KeyboardEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate, useParams } from "react-router";
import {
  Bot,
  CalendarDays,
  CheckCircle2,
  Clock,
  Download,
  FileWarning,
  Flag,
  FolderPlus,
  ListTodo,
  LogOut,
  Plus,
  RefreshCw,
  ShieldCheck,
  Target,
  Trash2,
  Upload,
  User,
  Users,
  Maximize2,
  Minimize2,
} from "lucide-react";
import { AnalyzeResult } from "../analysisTypes";
import { ApiError, RiskSimulationResult, analyzeProject, applyPriorityResultsToTasks, approveProjectSchedule, isProjectAnalysisStale, localProjectFingerprint, simulateRiskSuggestion, taskInfoFieldsFromError, userFacingApiError } from "../apiClient";
import { calendarEventHasLocalConflict, calendarEventPosition, calendarGridHeight, calendarHours } from "../calendarUtils";
import { taskDraftSchema } from "../schemas";
import { CalendarEvent, ImportanceLevel, LOCAL_DATA_NOTICE, PersistedStore, Project, RiskLevel, SlotQuality, Task, TaskStatus, mintId, parseExportPayload, summarizeClientMetrics, useAppStore } from "../store";
import { applyTaskJsonTemplate, applyTaskJsonTemplates } from "../taskJsonTemplate";

type AnalysisTab = "priority" | "schedule" | "risk";

const importanceLabel: Record<ImportanceLevel, string> = {
  low: "낮음",
  medium: "보통",
  high: "높음",
  critical: "중요",
};

const statusLabel: Record<TaskStatus, string> = {
  todo: "할 일",
  in_progress: "진행중",
  blocked: "막힘",
  review: "검토",
  done: "완료",
  cancelled: "취소",
};

const riskLabel: Record<RiskLevel, string> = {
  ok: "정상",
  watch: "관찰",
  at_risk: "주의",
  overdue: "지연",
};

const riskClass: Record<RiskLevel, string> = {
  ok: "border-[#d1d6db] bg-[#f2f4f6] text-[#4e5968]",
  watch: "border-yellow-200 bg-yellow-50 text-yellow-700",
  at_risk: "border-orange-200 bg-orange-50 text-orange-700",
  overdue: "border-[#f04452]/20 bg-[#ffeeee] text-[#d22030]",
};

const qualityLabel: Record<SlotQuality, string> = {
  preferred: "추천",
  acceptable: "가능",
  fallback: "주의",
};

const qualityClass: Record<SlotQuality, string> = {
  preferred: "bg-green-50 text-green-700",
  acceptable: "bg-amber-50 text-amber-700",
  fallback: "bg-orange-50 text-orange-700",
};

const factorLabels = {
  deadline: "마감",
  importance: "중요도",
  predecessor: "선행",
  progress: "진척",
  overload: "부하",
};

const riskGroupLabels = {
  deadline: "마감",
  dependency: "선후행",
  workload: "담당자 부하",
};

const riskCheckLabels: Record<string, string> = {
  deadline_feasibility: "마감일까지 완료 가능성",
  dependency_correctness: "선후행 관계 오류",
  workload_concentration: "담당자 업무 쏠림",
};

const softCheckLabels: Record<string, string> = {
  implicit_dependency_suspected: "암묵적 의존 의심",
  repeated_delay_root_cause: "반복 지연 원인",
  milestone_task_mismatch: "마일스톤-Task 정렬 불일치",
  task_definition_too_vague: "Task 정의 모호",
  duplicate_task_suspected: "중복 Task 의심",
};
export default function Dashboard() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const location = useLocation();
  const {
    projects,
    updateProject,
    currentUser,
    logout,
    exportJson,
    replaceStore,
    clientMetrics,
    recordAnalyzeLatency,
    recordSuggestionAcceptance,
  } = useAppStore();
  const [activeProjectId, setActiveProjectId] = useState(projectId ?? projects[projects.length - 1]?.id ?? "");
  const project = useMemo(
    () => projects.find((candidate) => candidate.id === activeProjectId) ?? projects[projects.length - 1],
    [activeProjectId, projects],
  );
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [analysisFingerprint, setAnalysisFingerprint] = useState("");
  const [apiError, setApiError] = useState("");
  const [apiErrorFields, setApiErrorFields] = useState<string[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [simulationBySuggestion, setSimulationBySuggestion] = useState<Record<string, RiskSimulationResult>>({});
  const [activeTab, setActiveTab] = useState<AnalysisTab>("priority");
  const [isCalendarExpanded, setIsCalendarExpanded] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<string[]>([]);
  const [ignoredSoftChecks, setIgnoredSoftChecks] = useState<string[]>([]);
  const [draftTask, setDraftTask] = useState(createEmptyTask(project?.id ?? ""));

  useEffect(() => {
    if (projects.length === 0) {
      setActiveProjectId("");
      return;
    }
    if (projectId && projects.some((candidate) => candidate.id === projectId)) {
      setActiveProjectId(projectId);
      return;
    }
    if (!projects.some((candidate) => candidate.id === activeProjectId)) {
      setActiveProjectId(projects[projects.length - 1].id);
    }
  }, [activeProjectId, projectId, projects]);

  useEffect(() => {
    if (location.pathname.endsWith("/calendar")) {
      setActiveTab("schedule");
      return;
    }
    if (location.pathname.endsWith("/tasks")) {
      setActiveTab("priority");
    }
  }, [location.pathname]);

  useEffect(() => {
    if (!project) return;
    setAnalysis(project.lastAnalysis ?? null);
    setAnalysisFingerprint(project.lastAnalysisFingerprint ?? "");
    setSelectedSchedule(project.lastAnalysis?.schedule.proposals.map((proposal) => proposal.taskId) ?? []);
    setSimulationBySuggestion({});
    setIgnoredSoftChecks([]);
    setApiErrorFields([]);
    setDraftTask(createEmptyTask(project.id));
  }, [project?.id]);

  const currentFingerprint = useMemo(() => (project ? localProjectFingerprint(project) : ""), [project]);
  const isStale = Boolean(analysis && isProjectAnalysisStale(project, analysisFingerprint));
  const metricSummary = useMemo(() => summarizeClientMetrics(clientMetrics), [clientMetrics]);
  const fallbackBadges = analysis
    ? [
        analysis.meta.llmFallbacks.scheduleRerankViolation ? "일정 추천 검토 필요" : null,
        analysis.meta.llmFallbacks.riskSoftChecksTimeout ? "리스크 확인 지연" : null,
      ].filter(Boolean)
    : [];

  const runAnalysisForProject = async (targetProject: Project, requestDecompositionFor: string[] = []) => {
    setIsAnalyzing(true);
    setApiError("");
    setApiErrorFields([]);
    const startedAt = performance.now();
    try {
      const next = await analyzeProject(targetProject, requestDecompositionFor);
      const prioritizedProject = applyPriorityResultsToTasks(targetProject, next);
      const nextFingerprint = localProjectFingerprint(prioritizedProject);
      recordAnalyzeLatency(targetProject.id, performance.now() - startedAt);
      setAnalysis(next);
      setAnalysisFingerprint(nextFingerprint);
      setSelectedSchedule(next.schedule.proposals.map((proposal) => proposal.taskId));
      updateProject(prioritizedProject.id, {
        ...prioritizedProject,
        lastAnalysis: next,
        lastAnalysisFingerprint: nextFingerprint,
      });
    } catch (error) {
      const message = error instanceof Error
          ? userFacingApiError(error, "분석 요청이 실패했습니다.")
          : "분석 요청이 실패했습니다.";
      setApiError(message);
      setApiErrorFields(taskInfoFieldsFromError(error));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const runAnalysis = async (requestDecompositionFor: string[] = []) => {
    if (!project) return;
    await runAnalysisForProject(project, requestDecompositionFor);
  };

  useEffect(() => {
    if (!project || !analysis || !isStale || isAnalyzing) return;
    const timer = window.setTimeout(() => {
      void runAnalysis();
    }, 600);
    return () => window.clearTimeout(timer);
  }, [project, analysis, isStale, isAnalyzing, currentFingerprint]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const importStore = (file: File | undefined) => {
    if (!file) return;
    file
      .text()
      .then((text) => {
        replaceStore(dropImportedAnalysis(parseExportPayload(text, file.size)));
        setApiError("");
      })
      .catch((error) => {
        setApiError(error instanceof Error ? error.message : "Import 파일을 읽지 못했습니다.");
      });
  };

  if (!project) {
    return (
      <div className="mx-auto max-w-5xl p-6">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">PM Agent</h1>
            <p className="mt-1 text-sm text-neutral-500">환영합니다, {currentUser?.name ?? "PM"}님</p>
          </div>
          <IconButton label="로그아웃" onClick={handleLogout}>
            <LogOut className="h-5 w-5" />
          </IconButton>
        </header>

        <div className="flex min-h-[520px] flex-col items-center justify-center rounded-lg border border-dashed border-neutral-300 bg-white px-6 text-center shadow-sm">
          <FolderPlus className="mb-4 h-14 w-14 text-neutral-300" />
          <h2 className="text-xl font-semibold text-neutral-900">프로젝트가 없습니다</h2>
          <p className="mt-2 max-w-md text-sm text-neutral-500">
            새 프로젝트를 만들면 G1 마일스톤 승인부터 Task 분석, G2 일정 승인까지 한 화면에서 이어집니다.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
            <button
              onClick={() => navigate("/new")}
              className="inline-flex items-center rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-800"
            >
              새 프로젝트 만들기
            </button>
            <label className="inline-flex cursor-pointer items-center rounded-lg border border-neutral-200 bg-white px-5 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
              <Download className="mr-2 h-4 w-4" />
              Import
              <input type="file" accept="application/json" className="hidden" onChange={(event) => importStore(event.target.files?.[0])} />
            </label>
          </div>
          {apiError && (
            <p className="mt-4 max-w-md text-sm text-amber-700">{apiError}</p>
          )}
        </div>
      </div>
    );
  }

  const upsertTask = () => {
    const parsedDraft = taskDraftSchema.safeParse(draftTask);
    if (!parsedDraft.success) {
      setApiError("Task 이름, 진척률, 예상 시간을 확인해 주세요.");
      return;
    }
    const exists = project.tasks.some((task) => task.id === draftTask.id);
    updateProject(project.id, {
      ...project,
      tasks: exists
        ? project.tasks.map((task) => (task.id === draftTask.id ? draftTask : task))
        : [...project.tasks, draftTask],
    });
    setDraftTask(createEmptyTask(project.id));
  };

  const deleteTask = (taskId: string) => {
    const task = project.tasks.find((candidate) => candidate.id === taskId);
    if (!task || !window.confirm(`"${task.title}" Task를 삭제할까요?`)) return;
    updateProject(project.id, {
      ...project,
      tasks: project.tasks
        .filter((candidate) => candidate.id !== taskId)
        .map((candidate) => ({
          ...candidate,
          predecessorIds: candidate.predecessorIds.filter((id) => id !== taskId),
        })),
      events: project.events.filter((event) => event.taskId !== taskId),
    });
    if (draftTask.id === taskId) {
      setDraftTask(createEmptyTask(project.id));
    }
    setAnalysis(null);
    setSelectedSchedule([]);
  };

  const applySuggestion = (patch: Partial<Task>, taskId: string) => {
    const task = project.tasks.find((candidate) => candidate.id === taskId);
    if (!task) return;
    const nextTask = { ...task, ...patch };
    updateProject(project.id, {
      ...project,
      tasks: project.tasks.map((candidate) => (candidate.id === taskId ? nextTask : candidate)),
    });
    setDraftTask(nextTask);
    setAnalysis(null);
    setSelectedSchedule([]);
  };

  const approveSelectedSchedule = async () => {
    if (!analysis) return;
    if (isProjectAnalysisStale(project, analysisFingerprint)) {
      setApiError("데이터가 변경되어 분석을 다시 실행합니다.");
      await runAnalysis();
      return;
    }
    setIsApproving(true);
    setApiError("");
    try {
      const result = await approveProjectSchedule(project, analysis, selectedSchedule, analysisFingerprint);
      recordSuggestionAcceptance(project.id, analysis.schedule.proposals.length, selectedSchedule.length);
      updateProject(project.id, result.project);
      setAnalysis(null);
      setSelectedSchedule([]);
      if (result.rejected.length > 0) {
        setApiError(`일부 일정이 거부되었습니다: ${result.rejected.map((item) => `${item.task_id}/${item.reason}`).join(", ")}`);
      }
    } catch (error) {
      if (error instanceof ApiError && error.code === "snapshot_hash_stale") {
        setApiError("데이터가 변경되어 분석을 다시 실행합니다.");
        await runAnalysis();
      } else {
        setApiError(userFacingApiError(error, "일정 승인 요청이 실패했습니다."));
      }
    } finally {
      setIsApproving(false);
    }
  };

  const updateCalendarEvent = (eventId: string, patch: Partial<CalendarEvent>) => {
    updateProject(project.id, {
      ...project,
      events: project.events.map((event) => (event.id === eventId ? { ...event, ...patch } : event)),
    });
  };

  const moveCalendarEventAndReanalyze = (eventId: string, patch: Partial<CalendarEvent>) => {
    const nextProject = {
      ...project,
      events: project.events.map((event) => (event.id === eventId ? { ...event, ...patch } : event)),
    };
    updateProject(project.id, nextProject);
    setActiveTab("schedule");
    if (analysis) {
      void runAnalysisForProject(nextProject);
    }
  };

  const chooseScheduleIndex = (taskId: string, selectedIndex: number) => {
    setAnalysis((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        schedule: {
          ...prev.schedule,
          proposals: prev.schedule.proposals.map((proposal) =>
            proposal.taskId === taskId ? { ...proposal, selectedIndex } : proposal,
          ),
        },
      };
    });
  };

  const setScheduleOverride = (
    taskId: string,
    field: "overrideDate" | "overrideStartTime" | "overrideEndTime",
    value: string,
  ) => {
    setAnalysis((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        schedule: {
          ...prev.schedule,
          proposals: prev.schedule.proposals.map((proposal) => {
            if (proposal.taskId !== taskId) return proposal;
            const selectedSlot = proposal.candidateSlots[proposal.selectedIndex];
            return {
              ...proposal,
              overrideDate: proposal.overrideDate ?? selectedSlot.date,
              overrideStartTime: proposal.overrideStartTime ?? selectedSlot.startTime,
              overrideEndTime: proposal.overrideEndTime ?? selectedSlot.endTime,
              [field]: value || undefined,
            };
          }),
        },
      };
    });
  };

  const simulateSuggestion = async (suggestionId: string) => {
    setApiError("");
    try {
      const result = await simulateRiskSuggestion(project, suggestionId);
      setSimulationBySuggestion((prev) => ({ ...prev, [suggestionId]: result }));
    } catch (error) {
      setApiError(userFacingApiError(error, "리스크 시뮬레이션 요청이 실패했습니다."));
    }
  };

  const downloadExport = () => {
    const blob = new Blob([exportJson()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "omc-pm-55-export.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const clearLocalData = () => {
    if (!window.confirm("로컬에 저장된 모든 프로젝트 데이터를 삭제할까요?")) return;
    replaceStore({
      schemaVersion: 1,
      currentUser,
      projects: [],
      clientMetrics: { analyzeLatenciesMs: [], suggestionAcceptanceEvents: [] },
    });
    setAnalysis(null);
    setSelectedSchedule([]);
    setDraftTask(createEmptyTask(""));
    setApiError("");
  };

  return (
    <div className="min-h-screen bg-[#f2f4f6] p-4 md:p-6 lg:p-8">
      <header className="mb-5 rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white p-5 shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <Target className="h-5 w-5 text-[#3182f6]" />
              <h1 className="text-2xl font-bold text-[#212529]">{project.name}</h1>
            </div>
            <p className="max-w-4xl text-sm text-[#4e5968]">{project.goal}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {projects.length > 1 && (
              <select
                value={project.id}
                onChange={(event) => setActiveProjectId(event.target.value)}
                className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529]"
                aria-label="프로젝트 선택"
              >
                {projects.map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.name}
                  </option>
                ))}
              </select>
            )}
            <button onClick={() => navigate("/new")} className="inline-flex items-center rounded-[7px] bg-[#191f28] px-3 py-2 text-sm font-semibold text-white hover:bg-[#4e5968] transition-colors">
              <FolderPlus className="mr-2 h-4 w-4" />
              새 프로젝트
            </button>
            <button onClick={downloadExport} className="inline-flex items-center rounded-[7px] border border-[rgba(0,27,55,0.1)] px-3 py-2 text-sm text-[#4e5968] hover:bg-[#f2f4f6] transition-colors">
              <Upload className="mr-2 h-4 w-4" />
              Export
            </button>
            <label className="inline-flex cursor-pointer items-center rounded-[7px] border border-[rgba(0,27,55,0.1)] px-3 py-2 text-sm text-[#4e5968] hover:bg-[#f2f4f6] transition-colors">
              <Download className="mr-2 h-4 w-4" />
              Import
              <input type="file" accept="application/json" className="hidden" onChange={(event) => importStore(event.target.files?.[0])} />
            </label>
            <button onClick={clearLocalData} className="inline-flex items-center rounded-[7px] border border-[#f04452]/20 px-3 py-2 text-sm text-[#f04452] hover:bg-[#ffeeee] transition-colors">
              <Trash2 className="mr-2 h-4 w-4" />
              Clear
            </button>
            <IconButton label="로그아웃" onClick={handleLogout}>
              <LogOut className="h-5 w-5" />
            </IconButton>
          </div>
        </div>
        <div className="mt-4 flex gap-3 rounded-[14px] border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <FileWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>{LOCAL_DATA_NOTICE}</p>
        </div>
        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-[7px] border border-[rgba(0,27,55,0.08)] bg-[#f9fafb] px-3 py-2 text-[#4e5968]">
            클라이언트 분석 P95: {metricSummary.analyzeP95Ms === null ? "측정 전" : `${metricSummary.analyzeP95Ms}ms`} · {metricSummary.analyzedSamples}회
          </div>
          <div className="rounded-[7px] border border-[rgba(0,27,55,0.08)] bg-[#f9fafb] px-3 py-2 text-[#4e5968]">
            추천 승인율: {metricSummary.suggestionAcceptanceRate === null ? "측정 전" : `${Math.round(metricSummary.suggestionAcceptanceRate * 100)}%`} · {metricSummary.suggestionEvents}회
          </div>
        </div>
      </header>

      <section className="mb-5 grid gap-4 xl:grid-cols-[1fr_1fr_1fr]" role="region" aria-label="프로젝트 개요">
        <ProjectSettings project={project} onUpdateProject={(nextProject) => updateProject(project.id, nextProject)} />
        <TeamSummary project={project} onUpdateProject={(nextProject) => updateProject(project.id, nextProject)} />
        <MilestoneSummary project={project} />
      </section>

      <main className={`grid gap-5 ${isCalendarExpanded ? "xl:grid-cols-[360px_minmax(0,1fr)]" : "xl:grid-cols-[360px_minmax(0,1fr)_360px]"}`}>
        <section className="rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
          <PanelHeader icon={<ListTodo className="h-5 w-5 text-[#4e5968]" />} title="Task 입력" />
          <div className="space-y-4 p-4">
            <TaskForm
              project={project}
              task={draftTask}
              errorFields={apiErrorFields}
              onChange={(nextTask) => {
                setDraftTask(nextTask);
                if (apiErrorFields.length) setApiErrorFields([]);
              }}
              onSubmit={upsertTask}
              onImportTasks={(tasks) => {
                updateProject(project.id, { ...project, tasks: [...project.tasks, ...tasks] });
                setDraftTask(createEmptyTask(project.id));
                if (apiErrorFields.length) setApiErrorFields([]);
              }}
              onCancel={() => {
                setDraftTask(createEmptyTask(project.id));
                setApiErrorFields([]);
              }}
            />
            <div className="space-y-3">
              {project.tasks.length === 0 ? (
                <EmptyState text="Task를 입력하면 분석 패널에서 우선순위, 일정안, 리스크가 함께 보입니다." />
              ) : (
                project.tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    project={project}
                    task={task}
                    riskLevel={analysis?.risk.taskRiskLevels[task.id]}
                    onEdit={() => setDraftTask(task)}
                    onDelete={() => deleteTask(task.id)}
                    onStatusChange={(status) =>
                      updateProject(project.id, {
                        ...project,
                        tasks: project.tasks.map((candidate) => (candidate.id === task.id ? { ...candidate, status } : candidate)),
                      })
                    }
                  />
                ))
              )}
            </div>
          </div>
        </section>

        {isCalendarExpanded ? (
          <div className="flex flex-col gap-5">
            <section className="rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
              <div className="flex items-center justify-between border-b border-[rgba(0,27,55,0.06)] p-4">
                <div className="flex items-center gap-2">
                  <CalendarDays className="h-5 w-5 text-[#4e5968]" />
                  <h2 className="font-bold text-[#212529]">내부 캘린더</h2>
                </div>
                <button
                  onClick={() => setIsCalendarExpanded(false)}
                  className="rounded-[7px] p-1.5 text-[#4e5968] hover:bg-[#f2f4f6] transition-colors"
                  title="캘린더 축소"
                >
                  <Minimize2 className="h-4 w-4" />
                </button>
              </div>
              <CalendarPanel
                project={project}
                onUpdateEvent={updateCalendarEvent}
                onMoveEvent={moveCalendarEventAndReanalyze}
                onReviewSchedule={() => setActiveTab("schedule")}
              />
            </section>

            <section className="rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
              <div className="flex flex-col gap-3 border-b border-[rgba(0,27,55,0.06)] p-4 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-[#3182f6]" />
                  <h2 className="font-bold text-[#212529]">AI 분석 패널</h2>
                  {isStale && (
                    <span className="rounded-[19px] border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
                      데이터 변경됨
                    </span>
                  )}
                  {fallbackBadges.map((badge) => (
                    <span key={badge} className="rounded-[19px] border border-orange-200 bg-orange-50 px-2 py-0.5 text-xs font-semibold text-orange-700">
                      {badge}
                    </span>
                  ))}
                </div>
                <button
                  onClick={() => runAnalysis()}
                  disabled={project.tasks.length === 0 || isAnalyzing}
                  className="inline-flex items-center justify-center rounded-[7px] bg-[#3182f6] px-4 py-2 text-sm font-semibold text-[#f9fafb] hover:bg-[#2272eb] disabled:opacity-50 transition-colors"
                >
                  <RefreshCw className={`mr-2 h-4 w-4 ${isAnalyzing ? "animate-spin" : ""}`} />
                  {isAnalyzing ? "분석 중" : "AI 분석 다시 실행"}
                </button>
              </div>

              {apiError && (
                <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {apiError}
                </div>
              )}

              <div className="border-b border-[rgba(0,27,55,0.06)] px-4 pt-3">
                <div className="flex gap-0">
                  {(["priority", "schedule", "risk"] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
                        activeTab === tab
                          ? "border-[#3182f6] text-[#3182f6]"
                          : "border-transparent text-[#4e5968] hover:text-[#212529]"
                      }`}
                    >
                      {tab === "priority" ? "우선순위" : tab === "schedule" ? "일정안" : "리스크"}
                    </button>
                  ))}
                </div>
              </div>

              <div className="min-h-[640px] p-4">
                {!analysis ? (
                  <EmptyAnalysis />
                ) : activeTab === "priority" ? (
                  <PriorityPanel
                    project={project}
                    analysis={analysis}
                    applySuggestion={applySuggestion}
                    requestDecomposition={(taskIds) => runAnalysis(taskIds)}
                  />
                ) : activeTab === "schedule" ? (
                  <SchedulePanel
                    project={project}
                    analysis={analysis}
                    selected={selectedSchedule}
                    setSelected={setSelectedSchedule}
                    approve={approveSelectedSchedule}
                    isApproving={isApproving}
                    chooseScheduleIndex={chooseScheduleIndex}
                    setScheduleOverride={setScheduleOverride}
                  />
                ) : (
                  <RiskPanel
                    project={project}
                    analysis={analysis}
                    applySuggestion={applySuggestion}
                    simulateSuggestion={simulateSuggestion}
                    simulationBySuggestion={simulationBySuggestion}
                    ignoredSoftChecks={ignoredSoftChecks}
                    ignoreSoftCheck={(checkId) => setIgnoredSoftChecks((prev) => [...new Set([...prev, checkId])])}
                  />
                )}
              </div>
            </section>
          </div>
        ) : (
          <>
            <section className="rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
              <div className="flex flex-col gap-3 border-b border-[rgba(0,27,55,0.06)] p-4 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-[#3182f6]" />
                  <h2 className="font-bold text-[#212529]">AI 분석 패널</h2>
                  {isStale && (
                    <span className="rounded-[19px] border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
                      데이터 변경됨
                    </span>
                  )}
                  {fallbackBadges.map((badge) => (
                    <span key={badge} className="rounded-[19px] border border-orange-200 bg-orange-50 px-2 py-0.5 text-xs font-semibold text-orange-700">
                      {badge}
                    </span>
                  ))}
                </div>
                <button
                  onClick={() => runAnalysis()}
                  disabled={project.tasks.length === 0 || isAnalyzing}
                  className="inline-flex items-center justify-center rounded-[7px] bg-[#3182f6] px-4 py-2 text-sm font-semibold text-[#f9fafb] hover:bg-[#2272eb] disabled:opacity-50 transition-colors"
                >
                  <RefreshCw className={`mr-2 h-4 w-4 ${isAnalyzing ? "animate-spin" : ""}`} />
                  {isAnalyzing ? "분석 중" : "AI 분석 다시 실행"}
                </button>
              </div>

              {apiError && (
                <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {apiError}
                </div>
              )}

              <div className="border-b border-[rgba(0,27,55,0.06)] px-4 pt-3">
                <div className="flex gap-0">
                  {(["priority", "schedule", "risk"] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
                        activeTab === tab
                          ? "border-[#3182f6] text-[#3182f6]"
                          : "border-transparent text-[#4e5968] hover:text-[#212529]"
                      }`}
                    >
                      {tab === "priority" ? "우선순위" : tab === "schedule" ? "일정안" : "리스크"}
                    </button>
                  ))}
                </div>
              </div>

              <div className="min-h-[640px] p-4">
                {!analysis ? (
                  <EmptyAnalysis />
                ) : activeTab === "priority" ? (
                  <PriorityPanel
                    project={project}
                    analysis={analysis}
                    applySuggestion={applySuggestion}
                    requestDecomposition={(taskIds) => runAnalysis(taskIds)}
                  />
                ) : activeTab === "schedule" ? (
                  <SchedulePanel
                    project={project}
                    analysis={analysis}
                    selected={selectedSchedule}
                    setSelected={setSelectedSchedule}
                    approve={approveSelectedSchedule}
                    isApproving={isApproving}
                    chooseScheduleIndex={chooseScheduleIndex}
                    setScheduleOverride={setScheduleOverride}
                  />
                ) : (
                  <RiskPanel
                    project={project}
                    analysis={analysis}
                    applySuggestion={applySuggestion}
                    simulateSuggestion={simulateSuggestion}
                    simulationBySuggestion={simulationBySuggestion}
                    ignoredSoftChecks={ignoredSoftChecks}
                    ignoreSoftCheck={(checkId) => setIgnoredSoftChecks((prev) => [...new Set([...prev, checkId])])}
                  />
                )}
              </div>
            </section>

            <section className="rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
              <div className="flex items-center justify-between border-b border-[rgba(0,27,55,0.06)] p-4">
                <div className="flex items-center gap-2">
                  <CalendarDays className="h-5 w-5 text-[#4e5968]" />
                  <h2 className="font-bold text-[#212529]">내부 캘린더</h2>
                </div>
                <button
                  onClick={() => setIsCalendarExpanded(true)}
                  className="rounded-[7px] p-1.5 text-[#4e5968] hover:bg-[#f2f4f6] transition-colors"
                  title="캘린더 확대"
                >
                  <Maximize2 className="h-4 w-4" />
                </button>
              </div>
              <CalendarPanel
                project={project}
                onUpdateEvent={updateCalendarEvent}
                onMoveEvent={moveCalendarEventAndReanalyze}
                onReviewSchedule={() => setActiveTab("schedule")}
              />
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function ProjectSettings({
  project,
  onUpdateProject,
}: {
  project: Project;
  onUpdateProject: (project: Project) => void;
}) {
  return (
    <section className="rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white p-4 shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
      <div className="mb-3 flex items-center gap-2">
        <Target className="h-5 w-5 text-[#4e5968]" />
        <h2 className="font-bold text-[#212529]">프로젝트 설정</h2>
      </div>
      <div className="space-y-2">
        <input
          value={project.name}
          onChange={(event) => onUpdateProject({ ...project, name: event.target.value })}
          className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6] focus:ring-1 focus:ring-[#3182f6]/20"
          aria-label="프로젝트 이름"
        />
        <textarea
          value={project.goal}
          onChange={(event) => onUpdateProject({ ...project, goal: event.target.value })}
          rows={3}
          className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6] focus:ring-1 focus:ring-[#3182f6]/20"
          aria-label="프로젝트 목표"
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            type="date"
            value={project.startsAt}
            onChange={(event) => onUpdateProject({ ...project, startsAt: event.target.value })}
            className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]"
            aria-label="프로젝트 시작일"
          />
          <input
            type="date"
            value={project.endsAt}
            onChange={(event) => onUpdateProject({ ...project, endsAt: event.target.value })}
            className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]"
            aria-label="프로젝트 종료일"
          />
        </div>
        <label className="block">
          <span className="mb-1 block text-xs font-bold text-[#4e5968]">기본 주간 시간</span>
          <input
            type="number"
            min={1}
            max={80}
            value={project.baseHours}
            onChange={(event) => onUpdateProject({ ...project, baseHours: Number(event.target.value) })}
            className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]"
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-xs font-bold text-[#4e5968]">평일 시작</span>
            <input
              type="time"
              value={project.defaultWorkStart ?? "09:00"}
              onChange={(event) => onUpdateProject({ ...project, defaultWorkStart: event.target.value })}
              className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-bold text-[#4e5968]">평일 종료</span>
            <input
              type="time"
              value={project.defaultWorkEnd ?? "18:00"}
              onChange={(event) => onUpdateProject({ ...project, defaultWorkEnd: event.target.value })}
              className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]"
            />
          </label>
        </div>
        <label className="flex items-center gap-2 text-xs font-bold text-[#4e5968]">
          <input
            type="checkbox"
            checked={project.weekendEnabled ?? false}
            onChange={(event) => onUpdateProject({ ...project, weekendEnabled: event.target.checked })}
            className="accent-[#3182f6]"
          />
          주말 근무 허용
        </label>
        {(project.weekendEnabled ?? false) && (
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="mb-1 block text-xs font-bold text-[#4e5968]">주말 시작</span>
              <input
                type="time"
                value={project.weekendWorkStart ?? "10:00"}
                onChange={(event) => onUpdateProject({ ...project, weekendWorkStart: event.target.value })}
                className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-bold text-[#4e5968]">주말 종료</span>
              <input
                type="time"
                value={project.weekendWorkEnd ?? "16:00"}
                onChange={(event) => onUpdateProject({ ...project, weekendWorkEnd: event.target.value })}
                className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]"
              />
            </label>
          </div>
        )}
      </div>
    </section>
  );
}

function TeamSummary({
  project,
  onUpdateProject,
}: {
  project: Project;
  onUpdateProject: (project: Project) => void;
}) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("Developer");
  const [hours, setHours] = useState(40);
  const [workStart, setWorkStart] = useState("09:00");
  const [workEnd, setWorkEnd] = useState("18:00");
  const addMember = () => {
    if (!name.trim() || workEnd <= workStart) return;
    onUpdateProject({
      ...project,
      members: [
        ...project.members,
        {
          id: mintId("mem"),
          name: name.trim(),
          role: role.trim() || "Member",
          availableHours: hours,
          workStart,
          workEnd,
        },
      ],
    });
    setName("");
  };
  const removeMember = (memberId: string) => {
    onUpdateProject({
      ...project,
      members: project.members.filter((member) => member.id !== memberId),
      tasks: project.tasks.map((task) => (task.assigneeId === memberId ? { ...task, assigneeId: null } : task)),
      events: project.events.map((event) => (event.assigneeId === memberId ? { ...event, assigneeId: null } : event)),
    });
  };

  return (
    <section className="rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white p-4 shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
      <div className="mb-3 flex items-center gap-2">
        <Users className="h-5 w-5 text-[#4e5968]" />
        <h2 className="font-bold text-[#212529]">팀원</h2>
      </div>
      <div className="mb-3 grid gap-2 rounded-[14px] border border-[rgba(0,27,55,0.06)] bg-[#f9fafb] p-3 sm:grid-cols-[1fr_1fr_76px_84px_84px_40px]">
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="이름" className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none focus:border-[#3182f6]" />
        <input value={role} onChange={(event) => setRole(event.target.value)} placeholder="역할" className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none focus:border-[#3182f6]" />
        <input type="number" min={0} max={80} value={hours} onChange={(event) => setHours(Number(event.target.value))} className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none focus:border-[#3182f6]" aria-label="주당 시간" />
        <input type="time" value={workStart} onChange={(event) => setWorkStart(event.target.value)} className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none focus:border-[#3182f6]" aria-label="근무 시작" />
        <input type="time" value={workEnd} onChange={(event) => setWorkEnd(event.target.value)} className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none focus:border-[#3182f6]" aria-label="근무 종료" />
        <button onClick={addMember} disabled={!name.trim() || workEnd <= workStart} className="inline-flex items-center justify-center rounded-[7px] bg-[#191f28] text-white hover:bg-[#4e5968] disabled:opacity-50 transition-colors" aria-label="팀원 추가">
          <Plus className="h-4 w-4" />
        </button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {project.members.map((member) => (
          <div key={member.id} className="rounded-[14px] border border-[rgba(0,27,55,0.08)] p-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="font-semibold text-[#212529]">{member.name}</div>
                <div className="text-xs text-[#4e5968]">{member.role}</div>
              </div>
              <button onClick={() => removeMember(member.id)} className="rounded-[7px] p-1 text-[#f04452] hover:bg-[#ffeeee] transition-colors" aria-label={`${member.name} 삭제`}>
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-2 text-xs font-semibold text-[#3182f6]">
              {member.availableHours}h/주 · {member.workStart}-{member.workEnd}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MilestoneSummary({ project }: { project: Project }) {
  return (
    <section className="rounded-[22px] border border-[rgba(0,27,55,0.08)] bg-white p-4 shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
      <div className="mb-3 flex items-center gap-2">
        <Flag className="h-5 w-5 text-[#4e5968]" />
        <h2 className="font-bold text-[#212529]">G1 승인 마일스톤</h2>
      </div>
      <div className="grid gap-2 md:grid-cols-3">
        {project.milestones.map((milestone, index) => (
          <div key={milestone.id} className="rounded-[14px] border border-[#e8f3ff] bg-[#f0f7ff] p-3">
            <div className="mb-1 text-xs font-bold text-[#3182f6]">M{index + 1} · {milestone.dueDate}</div>
            <div className="text-sm font-semibold text-[#212529]">{milestone.title}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function TaskField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0 space-y-1">
      <div className="h-4 truncate whitespace-nowrap text-xs leading-4 text-neutral-500">{label}</div>
      {children}
    </div>
  );
}

function TaskForm({
  project,
  task,
  errorFields,
  onChange,
  onSubmit,
  onImportTasks,
  onCancel,
}: {
  project: Project;
  task: Task;
  errorFields: string[];
  onChange: (task: Task) => void;
  onSubmit: () => void;
  onImportTasks: (tasks: Task[]) => void;
  onCancel: () => void;
}) {
  const taskForm = useForm<Pick<Task, "title" | "progress" | "estimatedHours">>({
    values: {
      title: task.title,
      progress: task.progress,
      estimatedHours: task.estimatedHours ?? 4,
    },
    mode: "onChange",
  });
  const titleField = taskForm.register("title");
  const progressField = taskForm.register("progress", { valueAsNumber: true });
  const estimatedHoursField = taskForm.register("estimatedHours", { valueAsNumber: true });
  const [isTemplateDragActive, setIsTemplateDragActive] = useState(false);
  const [templateNotice, setTemplateNotice] = useState("");
  const fieldClass = (field: string, base = "w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6] focus:ring-1 focus:ring-[#3182f6]/20") =>
    `${base} ${errorFields.includes(field) ? "!border-[#f04452] !bg-[#ffeeee] ring-1 !ring-[#f04452]/20" : ""}`;
  const handleTemplateDragOver = (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsTemplateDragActive(true);
  };
  const handleTemplateDrop = async (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsTemplateDragActive(false);
    const file = event.dataTransfer.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".json")) {
      setTemplateNotice("JSON 파일만 사용할 수 있습니다.");
      return;
    }

    try {
      const text = await file.text();
      const bulkResult = applyTaskJsonTemplates(project, task, text, file.size);
      if (bulkResult.tasks.length > 1) {
        onImportTasks(bulkResult.tasks);
        setTemplateNotice(
          bulkResult.warnings.length > 0
            ? `${bulkResult.tasks.length}개 Task를 추가했습니다. · ${bulkResult.warnings.join(" ")}`
            : `${bulkResult.tasks.length}개 Task를 추가했습니다.`,
        );
        return;
      }

      const result = applyTaskJsonTemplate(project, task, text, file.size);
      onChange(result.task);
      setTemplateNotice(
        result.warnings.length > 0
          ? `입력 완료 · ${result.warnings.join(" ")}`
          : `${file.name} 내용을 입력했습니다.`,
      );
    } catch (error) {
      setTemplateNotice(error instanceof Error ? error.message : "Task JSON을 읽지 못했습니다.");
    }
  };
  return (
    <form
      onSubmit={taskForm.handleSubmit(onSubmit)}
      onDragOver={handleTemplateDragOver}
      onDragLeave={() => setIsTemplateDragActive(false)}
      onDrop={handleTemplateDrop}
      className={`rounded-[14px] border bg-[#f9fafb] p-3 transition-colors ${
        isTemplateDragActive ? "border-[#3182f6] bg-[#e8f3ff]" : "border-[rgba(0,27,55,0.06)]"
      }`}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-bold text-[#212529]">핵심 필드</div>
        <div className="flex items-center gap-2">
          <a
            href="/task-template.json"
            download
            className="inline-flex items-center gap-1 rounded-[7px] border border-[rgba(0,27,55,0.08)] bg-white px-2 py-1 text-xs font-semibold text-[#4e5968] hover:bg-[#f2f4f6] transition-colors"
            aria-label="Task JSON 템플릿 다운로드"
          >
            <Download className="h-3.5 w-3.5" />
            템플릿
          </a>
          <span className="inline-flex items-center gap-1 rounded-[19px] border border-[rgba(0,27,55,0.08)] bg-white px-2 py-0.5 text-xs text-[#4e5968]">
            <Upload className="h-3.5 w-3.5" />
            JSON 드롭
          </span>
        </div>
      </div>
      {templateNotice && (
        <div className="mb-3 rounded-[10px] border border-[rgba(0,27,55,0.08)] bg-white px-3 py-2 text-xs font-medium text-[#4e5968]" role="status">
          {templateNotice}
        </div>
      )}
      <div className="space-y-3">
        <input
          name={titleField.name}
          ref={titleField.ref}
          onBlur={titleField.onBlur}
          value={task.title}
          onChange={(event) => {
            void titleField.onChange(event);
            onChange({ ...task, title: event.target.value });
          }}
          placeholder="Task 이름"
          className={fieldClass("title")}
        />
        <textarea value={task.description} onChange={(event) => onChange({ ...task, description: event.target.value })} placeholder="설명 / 완료 조건" rows={3} className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6] focus:ring-1 focus:ring-[#3182f6]/20" />
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <TaskField label="중요도">
            <select value={task.importance} onChange={(event) => onChange({ ...task, importance: event.target.value as ImportanceLevel })} className={fieldClass("importance")}>
              {Object.entries(importanceLabel).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </TaskField>
          <TaskField label="상태">
            <select value={task.status} onChange={(event) => onChange({ ...task, status: event.target.value as TaskStatus })} className={fieldClass("status")}>
              {Object.entries(statusLabel).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </TaskField>
          <TaskField label="담당자">
            <select value={task.assigneeId ?? ""} onChange={(event) => onChange({ ...task, assigneeId: event.target.value || null })} className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]">
              <option value="">담당자 미정</option>
              {project.members.map((member) => (
                <option key={member.id} value={member.id}>{member.name}</option>
              ))}
            </select>
          </TaskField>
          <TaskField label="마일스톤">
            <select value={task.milestoneId ?? ""} onChange={(event) => onChange({ ...task, milestoneId: event.target.value || null })} className="w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-3 py-2 text-sm text-[#212529] outline-none focus:border-[#3182f6]">
              <option value="">마일스톤 미지정</option>
              {project.milestones
                .filter((milestone) => milestone.status === "approved")
                .map((milestone) => (
                  <option key={milestone.id} value={milestone.id}>
                    {milestone.title}
                  </option>
                ))}
            </select>
          </TaskField>
          <TaskField label="데드라인">
            <input
              type="date"
              value={task.dueDate ?? ""}
              onChange={(event) => onChange({ ...task, dueDate: event.target.value || null })}
              className={fieldClass("dueDate")}
              aria-label="Task 데드라인"
            />
          </TaskField>
          <TaskField label="예상 시간">
            <input
              type="number"
              min={0.25}
              step={0.25}
              name={estimatedHoursField.name}
              ref={estimatedHoursField.ref}
              onBlur={estimatedHoursField.onBlur}
              value={task.estimatedHours ?? 4}
              onChange={(event) => {
                void estimatedHoursField.onChange(event);
                onChange({ ...task, estimatedHours: Number(event.target.value) });
              }}
              className={fieldClass("estimatedHours")}
            />
          </TaskField>
        </div>
        <textarea value={task.delayReason ?? ""} onChange={(event) => onChange({ ...task, delayReason: event.target.value || null })} placeholder="지연 사유" rows={2} className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm" />
        {project.tasks.filter((candidate) => candidate.id !== task.id).length > 0 && (
          <TaskField label="선행 Task">
            <div className="rounded-lg border border-neutral-200 bg-white p-2">
              <div className="space-y-1">
                {project.tasks
                  .filter((candidate) => candidate.id !== task.id)
                  .map((candidate) => (
                    <label key={candidate.id} className="flex items-center gap-2 text-xs text-neutral-700">
                      <input
                        type="checkbox"
                        checked={task.predecessorIds.includes(candidate.id)}
                        onChange={(event) =>
                          onChange({
                            ...task,
                            predecessorIds: event.target.checked
                              ? [...task.predecessorIds, candidate.id]
                              : task.predecessorIds.filter((id) => id !== candidate.id),
                          })
                        }
                      />
                      {candidate.title}
                    </label>
                  ))}
              </div>
            </div>
          </TaskField>
        )}
        <TaskField label="진척률">
          <div className="grid grid-cols-[1fr_88px] gap-2">
            <input
              type="range"
              min={0}
              max={100}
              name={progressField.name}
              ref={progressField.ref}
              onBlur={progressField.onBlur}
              value={task.progress}
              onChange={(event) => {
                void progressField.onChange(event);
                onChange({ ...task, progress: Number(event.target.value) });
              }}
              className="w-full"
            />
            <div className="rounded-[7px] border border-[rgba(0,27,55,0.08)] bg-white px-2 py-1 text-center text-sm font-semibold text-[#212529]">{task.progress}%</div>
          </div>
        </TaskField>
        <div className="flex gap-2">
          <button type="submit" disabled={!task.title.trim()} className="inline-flex flex-1 items-center justify-center rounded-[7px] bg-[#3182f6] px-3 py-2 text-sm font-semibold text-white hover:bg-[#2272eb] disabled:opacity-50 transition-colors">
            <Plus className="mr-2 h-4 w-4" />
            저장
          </button>
          <button type="button" onClick={onCancel} className="rounded-[7px] border border-[rgba(0,27,55,0.1)] px-3 py-2 text-sm font-medium text-[#4e5968] hover:bg-white transition-colors">초기화</button>
        </div>
      </div>
    </form>
  );
}

function TaskCard({
  project,
  task,
  riskLevel,
  onEdit,
  onDelete,
  onStatusChange,
}: {
  project: Project;
  task: Task;
  riskLevel?: RiskLevel;
  onEdit: () => void;
  onDelete: () => void;
  onStatusChange: (status: TaskStatus) => void;
}) {
  const assignee = project.members.find((member) => member.id === task.assigneeId);
  const milestone = project.milestones.find((candidate) => candidate.id === task.milestoneId);
  return (
    <div className={`rounded-[14px] border p-3 ${riskClass[riskLevel ?? "ok"]}`}>
      <div className="mb-2 flex items-start justify-between gap-3">
        <button onClick={onEdit} className="text-left text-sm font-bold text-[#212529] hover:underline">{task.title}</button>
        <span className="shrink-0 rounded-[19px] bg-white px-2 py-0.5 text-xs font-semibold">{riskLabel[riskLevel ?? "ok"]}</span>
      </div>
      <p className="line-clamp-2 text-xs text-[#4e5968]">{task.description || "설명 없음"}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-[#4e5968]">
        <span>{importanceLabel[task.importance]}</span>
        <span>{task.dueDate ?? "마감 미정"}</span>
        <span>{assignee?.name ?? "담당자 미정"}</span>
        <span>{task.estimatedHours ?? 4}h · {task.progress}%</span>
        <span className="col-span-2">{milestone ? `마일스톤 · ${milestone.title}` : "마일스톤 미지정"}</span>
      </div>
      <select value={task.status} onChange={(event) => onStatusChange(event.target.value as TaskStatus)} className="mt-3 w-full rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none">
        {Object.entries(statusLabel).map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>
      <div className="mt-2 flex justify-end">
        <button onClick={onDelete} className="inline-flex items-center rounded-[7px] border border-[#f04452]/20 bg-white px-2 py-1 text-xs font-semibold text-[#f04452] hover:bg-[#ffeeee] transition-colors">
          <Trash2 className="mr-1 h-3 w-3" />
          삭제
        </button>
      </div>
    </div>
  );
}

function PriorityPanel({
  project,
  analysis,
  applySuggestion,
  requestDecomposition,
}: {
  project: Project;
  analysis: AnalyzeResult;
  applySuggestion: (patch: Partial<Task>, taskId: string) => void;
  requestDecomposition: (taskIds: string[]) => void;
}) {
  const [selectedDecompositionIds, setSelectedDecompositionIds] = useState<string[]>([]);
  const toggleDecompositionSelection = (taskId: string, checked: boolean) => {
    setSelectedDecompositionIds((prev) => (checked ? [...new Set([...prev, taskId])] : prev.filter((id) => id !== taskId)));
  };
  const requestSelectedDecompositions = () => {
    if (selectedDecompositionIds.length === 0) return;
    requestDecomposition(selectedDecompositionIds);
    setSelectedDecompositionIds([]);
  };

  return (
    <div className="space-y-3">
      <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-2 rounded-[14px] border border-[rgba(0,27,55,0.08)] bg-white p-3 shadow-[0px_2px_30px_rgba(0,27,55,0.08)]">
        <div className="text-sm font-bold text-[#212529]">
          분해 요청 {selectedDecompositionIds.length}개 선택
        </div>
        <button
          onClick={requestSelectedDecompositions}
          disabled={selectedDecompositionIds.length === 0}
          className="rounded-[7px] border border-[rgba(0,27,55,0.1)] px-3 py-2 text-sm font-semibold text-[#4e5968] hover:bg-[#f2f4f6] disabled:opacity-50 transition-colors"
        >
          선택 Task 분해 요청 [G3]
        </button>
      </div>
      {analysis.priority.map((item) => {
        const task = project.tasks.find((candidate) => candidate.id === item.taskId);
        if (!task) return null;
        return (
          <div key={item.taskId} className="rounded-[14px] border border-[rgba(0,27,55,0.08)] p-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <label className="flex min-w-0 items-start gap-3">
                <input
                  type="checkbox"
                  checked={selectedDecompositionIds.includes(item.taskId)}
                  onChange={(event) => toggleDecompositionSelection(item.taskId, event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-[#d1d6db] accent-[#3182f6]"
                  aria-label={`${task.title} 분해 요청 선택`}
                />
                <span className="min-w-0">
                  <span className="block text-xs font-bold text-[#3182f6]">Rank {item.rank}</span>
                  <span className="block font-bold text-[#212529]">{task.title}</span>
                </span>
              </label>
              <span className="rounded-[14px] bg-[#e8f3ff] px-3 py-1 text-sm font-bold text-[#1b64da]">{item.score}/100</span>
            </div>
            <div className="space-y-2">
              {Object.entries(item.factors).map(([key, value]) => (
                <FactorBar key={key} label={factorLabels[key as keyof typeof factorLabels]} value={value} />
              ))}
            </div>
            <p className="mt-3 text-sm text-[#4e5968]">{item.rationale}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {item.evidenceFacts.map((fact) => (
                <span key={fact} className="rounded-[19px] bg-[#f2f4f6] px-2 py-1 text-xs text-[#4e5968]">{fact}</span>
              ))}
            </div>
            {analysis.decompositions
              .filter((decomposition) => decomposition.sourceTaskId === item.taskId)
              .map((decomposition) => (
                <div key={decomposition.sourceTaskId} className="mt-4 rounded-[14px] border border-[#e8f3ff] bg-[#f0f7ff] p-3">
                  <div className="mb-2 text-xs font-bold text-[#1b64da]">
                    분해 제안 · {Math.round(decomposition.confidence * 100)}% confidence
                  </div>
                  <div className="space-y-2">
                    {decomposition.subtasks.map((subtask, index) => (
                      <button
                        key={`${decomposition.sourceTaskId}-${index}`}
                        onClick={() =>
                          applySuggestion(
                            {
	                              id: mintId("task"),
	                              title: subtask.title,
	                              description: subtask.description ?? "",
	                              estimatedHours: subtask.estimated_hours_range[1],
	                              predecessorIds: [],
	                              progress: 0,
	                              status: "todo",
	                            },
                            task.id,
                          )
                        }
                        className="block w-full rounded-[7px] bg-white px-3 py-2 text-left text-xs text-[#212529] hover:bg-[#f9fafb] transition-colors"
	                      >
	                        <span className="font-semibold">{subtask.title}</span>
	                        <span className="ml-2 text-[#b0b8c1]">
	                          {subtask.estimated_hours_range[0]}-{subtask.estimated_hours_range[1]}h
	                        </span>
	                        <span className="mt-1 block text-[#3182f6] font-semibold">Task로 추가 [G3]</span>
	                      </button>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        );
      })}
    </div>
  );
}

function SchedulePanel({
  project,
  analysis,
  selected,
  setSelected,
  approve,
  isApproving,
  chooseScheduleIndex,
  setScheduleOverride,
}: {
  project: Project;
  analysis: AnalyzeResult;
  selected: string[];
  setSelected: (ids: string[]) => void;
  approve: () => void;
  isApproving: boolean;
  chooseScheduleIndex: (taskId: string, selectedIndex: number) => void;
  setScheduleOverride: (
    taskId: string,
    field: "overrideDate" | "overrideStartTime" | "overrideEndTime",
    value: string,
  ) => void;
}) {
  return (
    <div className="space-y-3">
      {analysis.schedule.unschedulable.length > 0 && (
        <div className="rounded-[14px] border border-amber-200 bg-amber-50 p-3">
          <div className="mb-2 text-sm font-bold text-amber-900">
            미배치 Task {analysis.schedule.unschedulable.length}건
          </div>
          <div className="space-y-2">
            {analysis.schedule.unschedulable.map((item) => {
              const task = project.tasks.find((candidate) => candidate.id === item.taskId);
              return (
                <div key={item.taskId} className="rounded-[7px] bg-white px-3 py-2 text-xs text-amber-800">
                  <div className="font-bold text-[#212529]">{task?.title ?? item.taskId}</div>
                  <div className="mt-1">{item.reason}</div>
                  <div className="mt-1 font-semibold text-amber-900">{unschedulablePmAction(project, task, item.reason)}</div>
                </div>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-amber-700">각 Task의 원인을 수정한 뒤 다시 분석하면 배치 가능 여부가 갱신됩니다.</p>
        </div>
      )}
      {analysis.schedule.proposals.map((proposal) => {
        const task = project.tasks.find((candidate) => candidate.id === proposal.taskId);
        const slot = proposal.candidateSlots[proposal.selectedIndex];
        return (
          <label key={proposal.taskId} className="block rounded-[14px] border border-[rgba(0,27,55,0.08)] p-4 hover:bg-[#f9fafb] transition-colors">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={selected.includes(proposal.taskId)}
                onChange={(event) =>
                  setSelected(event.target.checked ? [...selected, proposal.taskId] : selected.filter((id) => id !== proposal.taskId))
                }
                className="mt-1 h-4 w-4 rounded border-[#d1d6db] accent-[#3182f6]"
              />
              <div className="min-w-0 flex-1">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <h3 className="font-bold text-[#212529]">{task?.title}</h3>
                  <span className={`rounded-[19px] px-2 py-0.5 text-xs font-semibold ${qualityClass[slot.quality]}`}>
                    {qualityLabel[slot.quality]}
                  </span>
                  {slot.rerankSource === "llm_reranked" && <span className="rounded-[19px] bg-[#e8f3ff] px-2 py-0.5 text-xs font-semibold text-[#1b64da]">AI 정렬</span>}
                </div>
                <div className="flex flex-wrap gap-3 text-sm text-[#4e5968]">
                  <span className="inline-flex items-center"><Clock className="mr-1 h-4 w-4" />{slot.date} {slot.startTime}-{slot.endTime}</span>
                  {slot.timeBlocks.length > 1 && <span>근무 블록 {slot.timeBlocks.length}개</span>}
                  <span>fit {slot.fitScore}/100</span>
                  <span>충돌 {slot.conflicts.length}건</span>
                </div>
                {slot.rerankRationale && <p className="mt-2 text-xs text-[#4e5968]">AI 추천 이유: {slot.rerankRationale}</p>}
                {slot.timeBlocks.length > 1 && (
                  <div className="mt-3 rounded-[14px] border border-[rgba(0,27,55,0.06)] bg-[#f9fafb] p-3">
                    <div className="mb-2 text-xs font-bold text-[#4e5968]">분할 근무 블록</div>
                    <div className="flex flex-wrap gap-2 text-xs text-[#4e5968]">
                      {slot.timeBlocks.map((block) => (
                        <span key={`${proposal.taskId}-${block.date}-${block.startTime}-${block.endTime}`} className="rounded-full bg-white px-2 py-1 font-semibold">
                          {block.date} {block.startTime}-{block.endTime}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="mt-3 rounded-[14px] border border-[rgba(0,27,55,0.06)] bg-[#f9fafb] p-3">
                  <div className="mb-2 text-xs font-bold text-[#4e5968]">시간 직접 조정</div>
                  <div className="grid gap-2 sm:grid-cols-3">
                    <input
                      type="date"
                      value={proposal.overrideDate ?? slot.date}
                      onChange={(event) => setScheduleOverride(proposal.taskId, "overrideDate", event.target.value)}
                      className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none focus:border-[#3182f6]"
                    />
                    <input
                      type="time"
                      value={proposal.overrideStartTime ?? slot.startTime}
                      onChange={(event) => setScheduleOverride(proposal.taskId, "overrideStartTime", event.target.value)}
                      className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none focus:border-[#3182f6]"
                    />
                    <input
                      type="time"
                      value={proposal.overrideEndTime ?? slot.endTime}
                      onChange={(event) => setScheduleOverride(proposal.taskId, "overrideEndTime", event.target.value)}
                      className="rounded-[7px] border border-[rgba(0,27,55,0.1)] bg-white px-2 py-1.5 text-xs text-[#212529] outline-none focus:border-[#3182f6]"
                    />
                  </div>
                </div>
                {proposal.candidateSlots.length > 1 && (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-semibold text-[#4e5968]">다른 슬롯 보기</summary>
                    <div className="mt-2 space-y-2">
                      {proposal.candidateSlots.map((candidate, index) => (
                        <label key={`${proposal.taskId}-${candidate.date}-${candidate.startTime}`} className="flex items-center justify-between rounded-[7px] border border-[rgba(0,27,55,0.08)] bg-white px-3 py-2 text-xs">
                          <span>
                            <input
                              type="radio"
                              className="mr-2"
                              checked={proposal.selectedIndex === index}
                              onChange={() => chooseScheduleIndex(proposal.taskId, index)}
                            />
                            {candidate.date} {candidate.startTime}-{candidate.endTime}
                            {candidate.timeBlocks.length > 1 ? ` · ${candidate.timeBlocks.length}개 블록` : ""}
                          </span>
                          <span className="flex items-center gap-2">
                            <span className={`rounded-full px-2 py-0.5 font-medium ${qualityClass[candidate.quality]}`}>
                              {qualityLabel[candidate.quality]}
                            </span>
                            <span className="font-semibold text-[#4e5968]">fit {candidate.fitScore}</span>
                          </span>
                        </label>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </div>
          </label>
        );
      })}
      <button onClick={approve} disabled={selected.length === 0 || isApproving} className="sticky bottom-4 inline-flex w-full items-center justify-center rounded-[7px] bg-[#191f28] px-4 py-3 text-sm font-bold text-white shadow-[0px_2px_30px_rgba(0,27,55,0.2)] hover:bg-[#4e5968] disabled:opacity-50 transition-colors">
        <CheckCircle2 className="mr-2 h-4 w-4 text-green-400" />
        {isApproving ? "승인 중" : "선택한 일정 승인 [G2]"}
      </button>
    </div>
  );
}

function RiskPanel({
  project,
  analysis,
  applySuggestion,
  simulateSuggestion,
  simulationBySuggestion,
  ignoredSoftChecks,
  ignoreSoftCheck,
}: {
  project: Project;
  analysis: AnalyzeResult;
  applySuggestion: (patch: Partial<Task>, taskId: string) => void;
  simulateSuggestion: (suggestionId: string) => void;
  simulationBySuggestion: Record<string, RiskSimulationResult>;
  ignoredSoftChecks: string[];
  ignoreSoftCheck: (checkId: string) => void;
}) {
  const failedBlockers = analysis.risk.blockersFailed;
  const failedBlockerChecks = analysis.risk.checks.filter((check) => failedBlockers.includes(check.id));
  const visibleSoftChecks = analysis.risk.softChecks.filter((check) => !ignoredSoftChecks.includes(check.id));
  const riskDistribution = (["overdue", "at_risk", "watch", "ok"] as RiskLevel[]).map((level) => ({
    level,
    count: Object.values(analysis.risk.taskRiskLevels).filter((candidate) => candidate === level).length,
  }));
  const maxRiskCount = Math.max(1, ...riskDistribution.map((item) => item.count));
  const actionTextForSuggestion = (suggestion: AnalyzeResult["risk"]["suggestions"][number]) => {
    return suggestion.summary;
  };
  return (
    <div className="space-y-4">
      <div className={`rounded-[14px] border p-4 ${failedBlockers.length ? "border-[#f04452]/20 bg-[#ffeeee]" : "border-green-200 bg-green-50"}`}>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-bold text-[#212529]">리스크 요약</h3>
          <span className="rounded-[19px] bg-white px-2 py-1 text-xs font-bold text-[#212529]">
            blocker {failedBlockers.length}
          </span>
        </div>
        <p className="text-sm text-[#212529]">{analysis.risk.summary}</p>
        {failedBlockers.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {failedBlockerChecks.map((check) => (
              <span key={check.id} className="rounded-[19px] bg-white px-2 py-1 text-xs font-bold text-[#d22030]">
                {riskCheckLabels[check.id] ?? riskCheckLabels[check.label] ?? check.label}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {analysis.risk.checks.map((check) => {
          const suggestion = analysis.risk.suggestions.find((item) => item.fixesCheckIds.includes(check.id));
          const suggestionTask = suggestion ? project.tasks.find((task) => task.id === suggestion.taskId) : undefined;
          const displayTitle = suggestionTask?.title ?? riskCheckLabels[check.id] ?? riskCheckLabels[check.label] ?? check.label;
          return (
            <div key={check.id} className={`rounded-[14px] border p-3 ${check.status === "fail" ? "border-[#f04452]/20 bg-[#ffeeee]" : "border-[rgba(0,27,55,0.06)] bg-[#f9fafb]"}`}>
              <div className="mb-1 flex items-center justify-between">
                <span className="text-sm font-bold text-[#212529]">{displayTitle}</span>
                <span className="text-xs font-bold uppercase text-[#4e5968]">{check.status}</span>
              </div>
              <div className="mb-1 flex flex-wrap items-center gap-1 text-xs font-medium text-[#4e5968]">
                <span>{riskGroupLabels[check.group]}</span>
                <span>·</span>
                <span>{riskCheckLabels[check.id] ?? riskCheckLabels[check.label] ?? check.label}</span>
              </div>
              {check.status === "fail" && suggestionTask && (
                <div className="mb-1 text-xs font-semibold text-[#212529]">대상 Task: {suggestionTask.title}</div>
              )}
              <div className="text-xs text-[#4e5968]">{check.evidenceFacts.join(" · ")}</div>
              {check.status === "fail" && suggestion && (
                <div className="mt-2 rounded-[7px] border border-[#f04452]/20 bg-white px-2 py-1.5 text-xs font-semibold text-[#d22030]">
                  {actionTextForSuggestion(suggestion)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="rounded-[14px] border border-[rgba(0,27,55,0.08)] p-4">
        <h3 className="mb-3 text-sm font-bold text-[#212529]">Task 리스크 분포</h3>
        <div className="grid gap-2 sm:grid-cols-2">
          {riskDistribution.map((item) => (
            <div key={item.level}>
              <div className="mb-1 flex justify-between text-xs text-[#4e5968]">
                <span>{riskLabel[item.level]}</span>
                <span>{item.count}건</span>
              </div>
              <div className="h-2 rounded-full bg-[#f2f4f6]">
                <div
                  className={`h-2 rounded-full ${
                    item.level === "overdue"
                      ? "bg-[#f04452]"
                      : item.level === "at_risk"
                        ? "bg-orange-500"
                        : item.level === "watch"
                          ? "bg-yellow-500"
                          : "bg-[#b0b8c1]"
                  }`}
                  style={{ width: `${Math.round((item.count / maxRiskCount) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-[14px] border border-[rgba(0,27,55,0.08)] p-4">
        <h3 className="mb-3 flex items-center text-sm font-bold text-[#212529]">
          <ShieldCheck className="mr-2 h-4 w-4 text-[#4e5968]" />
          담당자 부하
        </h3>
        <div className="space-y-2">
          {analysis.risk.memberWorkload.map((workload) => {
            const member = project.members.find((candidate) => candidate.id === workload.memberId);
            return <FactorBar key={workload.memberId} label={member?.name ?? "미확인"} value={Math.min(workload.utilization, 1.4) / 1.4} suffix={`${workload.assignedHours}h`} />;
          })}
        </div>
      </div>

      <div className="rounded-[14px] border border-[#e8f3ff] bg-[#f0f7ff] p-4">
        <h3 className="mb-2 text-sm font-bold text-[#1b64da]">AI 직관 — PM 확인 필요</h3>
        {visibleSoftChecks.length === 0 ? (
          <p className="text-sm text-[#3182f6]">AI 직관에서 발견된 추가 위험 없음</p>
        ) : (
          <div className="space-y-2">
            {visibleSoftChecks.map((check) => (
              <div key={check.id} className="rounded-[14px] bg-white p-3">
                <div className="text-sm font-bold text-[#212529]">
                  {softCheckLabels[check.triggerLabel] ?? check.triggerLabel} · {Math.round(check.confidence * 100)}% 확신
                </div>
                <p className="mt-1 text-xs text-[#4e5968]">{check.userFacingText}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {check.involvedTaskIds.map((taskId) => (
                    <span key={taskId} className="rounded-[19px] bg-[#f2f4f6] px-2 py-1 text-xs text-[#4e5968]">{taskId}</span>
                  ))}
                </div>
                {check.supportingFacts.length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs font-semibold text-[#4e5968]">근거 보기</summary>
                    <div className="mt-1 text-xs text-[#4e5968]">{check.supportingFacts.join(" · ")}</div>
                  </details>
                )}
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.keys(check.patch).length > 0 && (
                    <button onClick={() => applySuggestion(check.patch, check.taskId)} className="rounded-[7px] border border-[rgba(0,27,55,0.1)] px-3 py-1.5 text-xs font-semibold text-[#212529] hover:bg-[#f2f4f6] transition-colors">
                      확인하고 적용 [G3]
                    </button>
                  )}
                  <button onClick={() => ignoreSoftCheck(check.id)} className="rounded-[7px] border border-[rgba(0,27,55,0.1)] px-3 py-1.5 text-xs font-semibold text-[#4e5968] hover:bg-[#f2f4f6] transition-colors">
                    무시
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-2">
        {analysis.risk.suggestions.map((suggestion) => {
          const hasApplicablePatch = Object.keys(suggestion.patch).length > 0;
          const isManualReschedule = suggestion.action === "reschedule" && !hasApplicablePatch;
          return (
            <div key={suggestion.id} className="rounded-[14px] border border-[rgba(0,27,55,0.08)] p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="font-bold text-[#212529]">{suggestion.summary}</div>
                {isManualReschedule && (
                  <span className="rounded-[19px] bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700">
                    수동 조정 필요
                  </span>
                )}
              </div>
              {suggestion.action === "reassign" && suggestion.targetMemberName && (
                <div className="mt-1 text-xs font-semibold text-[#3182f6]">
                  추천 담당자: {suggestion.targetMemberName}
                </div>
              )}
              <div className="mt-1 text-xs text-[#4e5968]">{suggestion.rationaleFacts.join(" · ")}</div>
              {simulationBySuggestion[suggestion.id] && (
                <div className="mt-2 rounded-[7px] bg-[#f9fafb] px-3 py-2 text-xs text-[#4e5968]">
                  <div>
                    변경 예상 체크: {simulationBySuggestion[suggestion.id].changed_check_ids.length ? simulationBySuggestion[suggestion.id].changed_check_ids.join(", ") : "변경 없음"}
                  </div>
                  {simulationBySuggestion[suggestion.id].score_action_coherence && (
                    <div className="mt-1">
                      우선순위 개선: +{simulationBySuggestion[suggestion.id].score_action_coherence.priority_delta}점 ·{" "}
                      {simulationBySuggestion[suggestion.id].score_action_coherence.passes_threshold ? "KPI 충족" : "KPI 미달"}
                    </div>
                  )}
                </div>
              )}
              {hasApplicablePatch && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button onClick={() => simulateSuggestion(suggestion.id)} className="rounded-[7px] border border-[rgba(0,27,55,0.1)] px-3 py-2 text-xs font-semibold text-[#4e5968] hover:bg-[#f2f4f6] transition-colors">
                    시뮬레이션
                  </button>
                  <button onClick={() => applySuggestion(suggestion.patch, suggestion.taskId)} className="rounded-[7px] bg-[#3182f6] px-3 py-2 text-xs font-semibold text-white hover:bg-[#2272eb] transition-colors">
                    {suggestion.action === "reassign" && suggestion.targetMemberName
                      ? `${suggestion.targetMemberName}로 담당자 지정 [G3]`
                      : "변경안 적용 [G3]"}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CalendarPanel({
  project,
  onUpdateEvent,
  onMoveEvent,
  onReviewSchedule,
}: {
  project: Project;
  onUpdateEvent: (eventId: string, patch: Partial<CalendarEvent>) => void;
  onMoveEvent: (eventId: string, patch: Partial<CalendarEvent>) => void;
  onReviewSchedule: () => void;
}) {
  const [view, setView] = useState<"week" | "day">("week");
  const [selectedDay, setSelectedDay] = useState("");
  const [draggedEventId, setDraggedEventId] = useState<string | null>(null);
  const approved = project.events.filter((event) => event.approved);
  if (approved.length === 0) return <EmptyState text="G2 승인된 일정만 캘린더에 표시됩니다." />;

  const firstEventDate = new Date(approved.map((event) => event.date).sort()[0]);
  const monday = new Date(firstEventDate);
  const day = monday.getDay();
  monday.setDate(monday.getDate() - (day === 0 ? 6 : day - 1));
  const weekDays = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(monday);
    date.setDate(monday.getDate() + index);
    return date.toISOString().slice(0, 10);
  });
  const grouped = approved.reduce((acc, event) => {
    (acc[event.date] = acc[event.date] ?? []).push(event);
    return acc;
  }, {} as Record<string, CalendarEvent[]>);
  const visibleDays = view === "day" ? [selectedDay || weekDays[0]] : weekDays;
  const moveSelectedDay = (delta: number) => {
    const currentIndex = Math.max(0, weekDays.indexOf(selectedDay || weekDays[0]));
    const nextIndex = Math.max(0, Math.min(weekDays.length - 1, currentIndex + delta));
    setSelectedDay(weekDays[nextIndex]);
    setView("day");
  };
  const handleCalendarKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      moveSelectedDay(1);
    }
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      moveSelectedDay(-1);
    }
  };

  return (
    <div className="p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-sm font-bold text-neutral-900">{view === "week" ? "Week" : "Day"}</div>
          <div className="text-xs text-neutral-500">{weekDays[0]} - {weekDays[6]}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-[7px] border border-[rgba(0,27,55,0.08)] bg-[#f2f4f6] p-1">
            {(["week", "day"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setView(mode)}
                className={`rounded-[5px] px-2 py-1 text-xs font-semibold transition-colors ${
                  view === mode ? "bg-[#191f28] text-white" : "text-[#4e5968] hover:text-[#212529]"
                }`}
              >
                {mode === "week" ? "Week" : "Day"}
              </button>
            ))}
          </div>
          <button onClick={onReviewSchedule} className="rounded-[7px] border border-[rgba(0,27,55,0.1)] px-2 py-1.5 text-xs font-semibold text-[#4e5968] hover:bg-[#f2f4f6] transition-colors">
            AI 일정 검토
          </button>
        </div>
      </div>
      {view === "day" && (
        <div className="mb-3 flex gap-1 overflow-x-auto pb-1">
          {weekDays.map((date) => (
            <button
              key={date}
              onClick={() => setSelectedDay(date)}
              className={`shrink-0 rounded-[7px] border px-2 py-1 text-xs font-semibold transition-colors ${
                (selectedDay || weekDays[0]) === date
                  ? "border-[#3182f6] bg-[#3182f6] text-white"
                  : "border-[rgba(0,27,55,0.1)] text-[#4e5968] hover:bg-[#f2f4f6]"
              }`}
            >
              {new Date(date).toLocaleDateString("ko-KR", { weekday: "short" })} {date.slice(5)}
            </button>
          ))}
        </div>
      )}
      <div
        role="grid"
        tabIndex={0}
        aria-label="승인된 내부 캘린더"
        onKeyDown={handleCalendarKeyDown}
        className={`grid overflow-hidden rounded-[14px] border border-[rgba(0,27,55,0.08)] focus:outline-none focus:ring-2 focus:ring-[#3182f6] focus:ring-offset-2 ${view === "week" ? "grid-cols-1 md:grid-cols-[44px_repeat(7,minmax(0,1fr))]" : "grid-cols-[44px_minmax(0,1fr)]"}`}
      >
        <div className="border-r border-[rgba(0,27,55,0.06)] bg-[#f9fafb]" role="presentation">
          <div className="h-12 border-b border-[rgba(0,27,55,0.06)]" />
          <div className="relative" style={{ height: calendarGridHeight() }}>
            {calendarHours().map((hour) => (
              <div key={hour} className="h-10 border-b border-neutral-100 pr-1 text-right text-[10px] font-medium text-neutral-400">
                {hour}:00
              </div>
            ))}
          </div>
        </div>
        {visibleDays.map((date) => {
          const events = [...(grouped[date] ?? [])].sort((a, b) => a.startTime.localeCompare(b.startTime));
          return (
            <div
              key={date}
              role="gridcell"
              aria-label={`${date} 일정`}
              onDragOver={(dragEvent) => {
                if (draggedEventId) dragEvent.preventDefault();
              }}
              onDrop={(dropEvent) => {
                dropEvent.preventDefault();
                if (!draggedEventId) return;
                onMoveEvent(draggedEventId, { date });
                setDraggedEventId(null);
              }}
              className="border-r border-neutral-200 bg-white last:border-r-0"
            >
              <div className="sticky top-0 z-10 h-12 border-b border-neutral-100 bg-white px-2 py-2" role="columnheader">
                <div className="text-xs font-bold text-neutral-900">
                  {new Date(date).toLocaleDateString("ko-KR", { weekday: "short" })}
                </div>
                <div className="text-xs text-neutral-500">{date.slice(5)}</div>
              </div>
              <div className="relative bg-white" style={{ height: calendarGridHeight() }}>
                {calendarHours().map((hour) => (
                  <div key={`${date}-${hour}`} className="h-10 border-b border-neutral-100" />
                ))}
                {events.length === 0 && <div className="absolute inset-x-2 top-3 rounded-lg border border-dashed border-neutral-100 p-3 text-center text-xs text-neutral-300">빈 일정</div>}
                {events.map((event) => {
                  const member = project.members.find((candidate) => candidate.id === event.assigneeId);
                  const hasInvalidRange = event.endTime <= event.startTime;
                  const hasLocalConflict = calendarEventHasLocalConflict(event, approved);
                  const position = calendarEventPosition(event);
                  return (
                    <details
                      key={event.id}
                      draggable
                      onDragStart={() => setDraggedEventId(event.id)}
                      onDragEnd={() => setDraggedEventId(null)}
                      aria-label={`${event.title} 일정 카드. 드래그해서 날짜를 변경하면 재분석됩니다.`}
                      className={`absolute inset-x-1 cursor-grab overflow-hidden rounded-[7px] border p-2 shadow-sm active:cursor-grabbing ${
                        hasInvalidRange || hasLocalConflict ? "border-[#f04452]/40 bg-[#ffeeee]" : "border-[#e8f3ff] bg-[#f0f7ff]"
                      }`}
                      style={{ top: position.top, minHeight: position.height }}
                    >
                      <summary className="cursor-pointer list-none">
                        <div className="mb-1 text-xs font-bold text-[#3182f6]">{event.startTime}-{event.endTime}</div>
                        <div className="text-xs font-semibold text-[#212529]">{event.title}</div>
                        <div className="mt-2 flex items-center text-xs text-[#4e5968]">
                          <User className="mr-1 h-3 w-3" />
                          {member?.name ?? "미배정"}
                        </div>
                      </summary>
                      <div className="mt-3 grid gap-2">
                        <input
                          type="date"
                          value={event.date}
                          onChange={(change) => onUpdateEvent(event.id, { date: change.target.value })}
                          className="rounded-lg border border-blue-100 bg-white px-2 py-1 text-xs"
                          aria-label={`${event.title} 날짜 수정`}
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            type="time"
                            value={event.startTime}
                            onChange={(change) => onUpdateEvent(event.id, { startTime: change.target.value })}
                            className="rounded-lg border border-blue-100 bg-white px-2 py-1 text-xs"
                            aria-label={`${event.title} 시작 시간 수정`}
                          />
                          <input
                            type="time"
                            value={event.endTime}
                            onChange={(change) => onUpdateEvent(event.id, { endTime: change.target.value })}
                            className="rounded-lg border border-blue-100 bg-white px-2 py-1 text-xs"
                            aria-label={`${event.title} 종료 시간 수정`}
                          />
                        </div>
                        {hasInvalidRange && <div className="text-xs font-medium text-red-600">종료 시간이 시작 시간보다 늦어야 합니다.</div>}
                        {!hasInvalidRange && hasLocalConflict && <div className="text-xs font-medium text-red-600">같은 담당자의 다른 일정과 겹칩니다.</div>}
                      </div>
                    </details>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FactorBar({ label, value, suffix }: { label: string; value: number; suffix?: string }) {
  const width = `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-[#4e5968]">
        <span>{label}</span>
        <span>{suffix ?? width}</span>
      </div>
      <div className="h-2 rounded-full bg-[#f2f4f6]">
        <div className="h-2 rounded-full bg-[#3182f6]" style={{ width }} />
      </div>
    </div>
  );
}

function EmptyAnalysis() {
  return (
    <div className="flex min-h-[560px] flex-col items-center justify-center text-center">
      <Bot className="mb-4 h-14 w-14 text-[#d1d6db]" />
      <h3 className="font-bold text-[#212529]">분석 대기 중</h3>
      <p className="mt-2 max-w-md text-sm text-[#4e5968]">
        Task를 저장한 뒤 Backend 분석 API를 호출하면 우선순위, 일정안, 리스크가 표시됩니다.
      </p>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center rounded-[14px] border border-dashed border-[#d1d6db] p-6 text-center text-sm text-[#6b7684]">
      <FileWarning className="mb-3 h-8 w-8 text-[#b0b8c1]" />
      {text}
    </div>
  );
}

function unschedulablePmAction(project: Project, task: Task | undefined, reason: string) {
  const title = task?.title ?? "이 Task";
  if (reason.includes("assignee_missing") || reason.includes("missing_assignee")) {
    return `AI 제안: '${title}' 담당자를 지정한 뒤 다시 분석하세요.`;
  }
  if (reason.includes("estimated_hours_missing")) {
    return `AI 제안: '${title}' 예상 시간을 입력한 뒤 다시 분석하세요.`;
  }
  if (reason.includes("predecessor_incomplete")) {
    const blockers = task?.predecessorIds
      .map((id) => project.tasks.find((candidate) => candidate.id === id))
      .filter((candidate): candidate is Task => candidate !== undefined && candidate.status !== "done" && candidate.status !== "cancelled")
      .map((candidate) => candidate.title);
    const blockerText = blockers?.length ? blockers.slice(0, 2).join(", ") : "선행 Task";
    return `AI 제안: '${title}'의 선행 관계에서 '${blockerText}' 연결을 제거하는 변경안을 리스크 탭에서 적용하세요.`;
  }
  if (reason.includes("no_capacity_before_deadline")) {
    return `AI 제안: '${title}' 마감일 변경안을 리스크 탭에서 적용하세요.`;
  }
  if (reason.includes("deadline_in_past")) {
    return `AI 제안: '${title}' 마감일을 오늘 이후로 조정하세요.`;
  }
  return `AI 제안: '${title}'의 미배치 원인을 수정한 뒤 다시 분석하세요.`;
}

function PanelHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-[rgba(0,27,55,0.06)] p-4">
      {icon}
      <h2 className="font-bold text-[#212529]">{title}</h2>
    </div>
  );
}

function IconButton({ label, children, onClick }: { label: string; children: React.ReactNode; onClick: () => void }) {
  return (
    <button onClick={onClick} title={label} aria-label={label} className="rounded-[7px] p-2 text-[#4e5968] hover:bg-[#f2f4f6] transition-colors">
      {children}
    </button>
  );
}

function createEmptyTask(projectId: string): Task {
  return {
    id: mintId("task"),
    title: "",
    description: "",
    assigneeId: null,
    milestoneId: null,
    importance: "medium",
    status: "todo",
    progress: 0,
    estimatedHours: 4,
    dueDate: null,
    predecessorIds: [],
    delayReason: null,
  };
}

function dropImportedAnalysis(store: PersistedStore): PersistedStore {
  return {
    ...store,
    projects: store.projects.map((project) => ({
      ...project,
      lastAnalysis: undefined,
      lastAnalysisFingerprint: undefined,
    })),
  };
}
