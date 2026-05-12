import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createServer } from "vite";

const server = await createServer({
  configFile: new URL("../vite.config.ts", import.meta.url).pathname,
  root: new URL("..", import.meta.url).pathname,
  server: { middlewareMode: true },
  appType: "custom",
  logLevel: "error",
});

try {
  const {
    API_BASE,
    ApiError,
    applyPriorityAssignments,
    applyPriorityResultsToTasks,
    approveProjectSchedule,
    buildSnapshotForApi,
    isProjectAnalysisStale,
    localProjectFingerprint,
    mapAnalyze,
    patchForAction,
    taskInfoFieldsFromError,
    userFacingApiError,
  } = await server.ssrLoadModule("/src/app/apiClient.ts");
  const {
    calendarEventHasLocalConflict,
    calendarEventPosition,
    calendarGridHeight,
    calendarHours,
  } = await server.ssrLoadModule("/src/app/calendarUtils.ts");
  const { LOCAL_DATA_NOTICE, MAX_EXPORT_BYTES, mintId, parseExportPayload, summarizeClientMetrics } = await server.ssrLoadModule("/src/app/store.tsx");
  const { applyTaskJsonTemplate, applyTaskJsonTemplates } = await server.ssrLoadModule("/src/app/taskJsonTemplate.ts");
  const project = {
    id: "proj_TEST0001",
    name: "Milestone Snapshot",
    goal: "Task milestone contract",
    startsAt: "2026-05-07",
    endsAt: "2026-06-30",
    baseHours: 40,
    defaultWorkStart: "08:30",
    defaultWorkEnd: "17:30",
    weekendEnabled: true,
    weekendWorkStart: "11:00",
    weekendWorkEnd: "15:00",
    members: [
      {
        id: "mem_TEST01",
        name: "Backend",
        role: "Engineer",
        availableHours: 32,
        workStart: "10:00",
        workEnd: "17:00",
      },
    ],
    milestones: [
      {
        id: "ms_approved",
        title: "Approved milestone",
        dueDate: "2026-05-20",
        status: "approved",
      },
    ],
    tasks: [
      {
        id: "task_LINK0001",
        milestoneId: "ms_approved",
        title: "Linked task",
        description: "Should keep the selected milestone id",
        assigneeId: null,
        importance: "high",
        status: "todo",
        progress: 0,
        estimatedHours: 4,
        dueDate: "2026-05-18",
        predecessorIds: [],
        delayReason: null,
      },
    ],
    events: [],
  };
  const snapshot = buildSnapshotForApi(project);
  const taskTemplateResult = applyTaskJsonTemplate(
    project,
    project.tasks[0],
    JSON.stringify({
      title: "드롭된 JSON Task",
      description: "JSON 파일에서 가져온 완료 조건",
      importance: "critical",
      status: "blocked",
      assigneeName: "Backend",
      milestoneTitle: "Approved milestone",
      dueDate: "2026-05-22",
      estimatedHours: 6.5,
      progress: 35,
      delayReason: "외부 API 대기",
    }),
  );

  assert.equal(taskTemplateResult.task.title, "드롭된 JSON Task");
  assert.equal(taskTemplateResult.task.description, "JSON 파일에서 가져온 완료 조건");
  assert.equal(taskTemplateResult.task.importance, "critical");
  assert.equal(taskTemplateResult.task.status, "blocked");
  assert.equal(taskTemplateResult.task.assigneeId, "mem_TEST01");
  assert.equal(taskTemplateResult.task.milestoneId, "ms_approved");
  assert.equal(taskTemplateResult.task.dueDate, "2026-05-22");
  assert.equal(taskTemplateResult.task.estimatedHours, 6.5);
  assert.equal(taskTemplateResult.task.progress, 35);
  assert.equal(taskTemplateResult.task.delayReason, "외부 API 대기");
  const bulkIds = ["task_BULK0001", "task_BULK0002"];
  const bulkTemplateResult = applyTaskJsonTemplates(
    project,
    project.tasks[0],
    JSON.stringify({
      tasks: [
        {
          title: "첫 번째 Bulk Task",
          description: "전체 JSON 드롭 첫 항목",
          milestoneTitle: "Approved milestone",
          dueDate: "2026-05-23",
          estimatedHours: 3,
        },
        {
          title: "두 번째 Bulk Task",
          description: "첫 번째 Task를 선행으로 연결한다.",
          milestoneTitle: "Approved milestone",
          dueDate: "2026-05-24",
          estimatedHours: 5,
          predecessorTitles: ["첫 번째 Bulk Task"],
        },
      ],
    }),
    undefined,
    () => (bulkIds.shift() ?? "task_BULK9999"),
  );

  assert.equal(bulkTemplateResult.tasks.length, 2);
  assert.equal(bulkTemplateResult.tasks[0].id, "task_BULK0001");
  assert.equal(bulkTemplateResult.tasks[0].assigneeId, null);
  assert.equal(bulkTemplateResult.tasks[0].milestoneId, "ms_approved");
  assert.equal(bulkTemplateResult.tasks[1].id, "task_BULK0002");
  assert.deepEqual(bulkTemplateResult.tasks[1].predecessorIds, ["task_BULK0001"]);
  assert.deepEqual(bulkTemplateResult.warnings, []);

  assert.equal(API_BASE, "http://127.0.0.1:8000");
  assert.match(LOCAL_DATA_NOTICE, /브라우저/);
  assert.match(LOCAL_DATA_NOTICE, /Export|백업/);
  assert.match(LOCAL_DATA_NOTICE, /삭제/);
  assert.deepEqual(
    summarizeClientMetrics({
      analyzeLatenciesMs: [
        { projectId: "proj_TEST0001", latencyMs: 1200, recordedAt: "2026-05-07T09:00:00+09:00" },
        { projectId: "proj_TEST0001", latencyMs: 900, recordedAt: "2026-05-07T09:01:00+09:00" },
        { projectId: "proj_TEST0001", latencyMs: 1500, recordedAt: "2026-05-07T09:02:00+09:00" },
      ],
      suggestionAcceptanceEvents: [
        { projectId: "proj_TEST0001", totalSuggestions: 5, acceptedSuggestions: 3, recordedAt: "2026-05-07T09:03:00+09:00" },
        { projectId: "proj_TEST0001", totalSuggestions: 5, acceptedSuggestions: 4, recordedAt: "2026-05-07T09:04:00+09:00" },
      ],
    }),
    {
      analyzeP95Ms: 1500,
      suggestionAcceptanceRate: 0.7,
      analyzedSamples: 3,
      suggestionEvents: 2,
    },
  );
  assert.deepEqual(snapshot.project.default_working_hours, {
    weekday: { start: "08:30", end: "17:30", enabled: true },
    weekend: { start: "11:00", end: "15:00", enabled: true },
  });
  assert.equal(snapshot.tasks[0].milestone_id, "ms_approved");
  assert.equal(snapshot.members[0].weekly_capacity_hours, 32);
  assert.equal(snapshot.members[0].available_hours.length, 5);
  assert.deepEqual(snapshot.members[0].available_hours[0], {
    day_of_week: 0,
    start: "10:00",
    end: "17:00",
  });
  assert.equal(snapshot.tasks[0].created_at, "2026-05-07T09:00:00+09:00");
  assert.equal(snapshot.tasks[0].updated_at, "2026-05-07T09:00:00+09:00");
  assert.equal(
    buildSnapshotForApi({
      ...project,
      baseHours: 28,
      members: [{ ...project.members[0], availableHours: undefined }],
    }).members[0].weekly_capacity_hours,
    28,
  );
  const prioritizedProject = applyPriorityResultsToTasks(
    {
      ...project,
      tasks: [
        project.tasks[0],
        {
          ...project.tasks[0],
          id: "task_ASSIGNED01",
          assigneeId: "mem_EXISTING01",
        },
        {
          ...project.tasks[0],
          id: "task_BLOCKED01",
          assigneeId: null,
          status: "blocked",
        },
      ],
    },
    {
      priority: [
        {
          taskId: "task_LINK0001",
          rank: 1,
          score: 87,
          factors: {
            deadline: 0.9,
            importance: 0.75,
            predecessor: 0.2,
            progress: 1,
            overload: 0,
          },
          evidenceFacts: ["마감까지 3일"],
          rationale: "마감까지 3일이라 먼저 확인합니다.",
        },
      ],
      taskAssignments: [
        {
          taskId: "task_LINK0001",
          assigneeId: "mem_TEST01",
          rationaleFacts: ["role_hint=none", "member role=Engineer"],
          rationale: "부하가 가장 낮은 담당자에게 배정했습니다.",
        },
        {
          taskId: "task_ASSIGNED01",
          assigneeId: "mem_TEST01",
          rationaleFacts: ["role_hint=none", "member role=Engineer"],
          rationale: "이미 담당자가 있으면 유지합니다.",
        },
        {
          taskId: "task_BLOCKED01",
          assigneeId: "mem_TEST01",
          rationaleFacts: ["role_hint=none", "member role=Engineer"],
          rationale: "blocked task는 자동 배정하지 않습니다.",
        },
      ],
    },
  );
  assert.equal(prioritizedProject.tasks[0].assigneeId, "mem_TEST01");
  assert.equal(prioritizedProject.tasks[0].priorityScore, 87);
  assert.equal(prioritizedProject.tasks[0].priorityRank, 1);
  assert.deepEqual(prioritizedProject.tasks[0].priorityFactors, {
    deadline: 0.9,
    importance: 0.75,
    predecessor: 0.2,
    progress: 1,
    overload: 0,
  });
  assert.deepEqual(prioritizedProject.tasks[0].priorityEvidenceFacts, ["마감까지 3일"]);
  assert.equal(prioritizedProject.tasks[0].priorityRationale, "마감까지 3일이라 먼저 확인합니다.");
  assert.match(prioritizedProject.tasks[0].priorityUpdatedAt, /^\d{4}-\d{2}-\d{2}T/);
  assert.equal(prioritizedProject.tasks[1].assigneeId, "mem_EXISTING01");
  assert.equal(prioritizedProject.tasks[2].assigneeId, null);
  assert.equal(project.tasks[0].assigneeId, null);
  const priorityOnlyProject = applyPriorityResultsToTasks(project, {
    priority: [
      {
        taskId: "task_LINK0001",
        rank: 2,
        score: 64,
        factors: {
          deadline: 0.6,
          importance: 0.75,
          predecessor: 0,
          progress: 0.2,
          overload: 0,
        },
        evidenceFacts: ["마감까지 7일"],
        rationale: "마감과 중요도 기준으로 확인합니다.",
      },
    ],
    taskAssignments: [],
  });
  assert.equal(priorityOnlyProject.tasks[0].assigneeId, null);
  assert.equal(
    localProjectFingerprint(project),
    localProjectFingerprint(priorityOnlyProject),
  );
  const prioritizedSnapshot = buildSnapshotForApi(prioritizedProject);
  assert.equal(Object.hasOwn(prioritizedSnapshot.tasks[0], "priorityScore"), false);
  assert.equal(Object.hasOwn(prioritizedSnapshot.tasks[0], "priorityFactors"), false);
  assert.equal(Object.hasOwn(prioritizedSnapshot.tasks[0], "priority_evidence_facts"), false);
  assert.equal(
    localProjectFingerprint(project),
    localProjectFingerprint({
      ...project,
      tasks: [
        {
          ...project.tasks[0],
          priorityScore: 87,
          priorityRank: 1,
          priorityFactors: {
            deadline: 0.9,
            importance: 0.75,
            predecessor: 0.2,
            progress: 1,
            overload: 0,
          },
          priorityEvidenceFacts: ["마감까지 3일"],
          priorityRationale: "마감까지 3일이라 먼저 확인합니다.",
          priorityUpdatedAt: "2026-05-10T12:00:00.000Z",
        },
      ],
    }),
  );
  const assignedProject = applyPriorityAssignments(project, {
    taskAssignments: [
      {
        taskId: "task_LINK0001",
        assigneeId: "mem_TEST01",
        rationaleFacts: ["role_hint=none", "member role=Engineer"],
        rationale: "부하가 가장 낮은 담당자에게 배정했습니다.",
      },
    ],
  });
  assert.equal(assignedProject.tasks[0].assigneeId, "mem_TEST01");
  assert.equal(project.tasks[0].assigneeId, null);
  const largeProject = {
    ...project,
    members: Array.from({ length: 5 }, (_, index) => ({
      id: `mem_PERF0${index}`,
      name: `Member ${index}`,
      role: "Engineer",
      availableHours: 32,
      workStart: "09:00",
      workEnd: "18:00",
    })),
    tasks: Array.from({ length: 100 }, (_, index) => ({
      ...project.tasks[0],
      id: `task_PERF${String(index).padStart(4, "0")}`,
      title: `Performance task ${index}`,
      assigneeId: `mem_PERF0${index % 5}`,
      predecessorIds: index > 0 ? [`task_PERF${String(index - 1).padStart(4, "0")}`] : [],
    })),
  };
  const perfStartedAt = performance.now();
  JSON.stringify(buildSnapshotForApi(largeProject));
  localProjectFingerprint(largeProject);
  const snapshotBuildMs = performance.now() - perfStartedAt;
  assert.ok(snapshotBuildMs <= 50, `snapshot build took ${snapshotBuildMs.toFixed(2)}ms`);
  assert.equal(calendarHours().length, 18);
  assert.equal(calendarGridHeight(), 720);
  assert.deepEqual(calendarEventPosition({ startTime: "09:00", endTime: "10:30" }), { top: 120, height: 60 });
  const calendarEvents = Array.from({ length: 50 }, (_, index) => ({
    id: `evt_PERF${String(index).padStart(4, "0")}`,
    taskId: `task_PERF${String(index).padStart(4, "0")}`,
    title: `Calendar event ${index}`,
    date: "2026-05-18",
    assigneeId: `mem_PERF0${index % 5}`,
    startTime: `${String(6 + (index % 12)).padStart(2, "0")}:00`,
    endTime: `${String(7 + (index % 12)).padStart(2, "0")}:00`,
    approved: true,
    source: "ai_suggested",
  }));
  const calendarStartedAt = performance.now();
  for (const event of calendarEvents) {
    calendarEventPosition(event);
    calendarEventHasLocalConflict(event, calendarEvents);
  }
  const calendarLayoutMs = performance.now() - calendarStartedAt;
  assert.ok(calendarLayoutMs <= 100, `calendar layout took ${calendarLayoutMs.toFixed(2)}ms`);
  assert.deepEqual(patchForAction(project, "task_LINK0001", { type: "add_predecessor", to: "task_BLOCK001" }), {
    predecessorIds: ["task_BLOCK001"],
  });
  assert.deepEqual(
    patchForAction(
      {
        ...project,
        tasks: [{ ...project.tasks[0], predecessorIds: ["task_BLOCK001"] }],
      },
      "task_LINK0001",
      { type: "add_predecessor", to: "task_BLOCK001" },
    ),
    { predecessorIds: ["task_BLOCK001"] },
  );
  assert.deepEqual(
    patchForAction(
      {
        ...project,
        tasks: [{ ...project.tasks[0], predecessorIds: ["task_BLOCK001", "task_OTHER001"] }],
      },
      "task_LINK0001",
      { type: "remove_predecessor", to: "task_BLOCK001" },
    ),
    { predecessorIds: ["task_OTHER001"] },
  );
  assert.deepEqual(patchForAction(project, "task_LINK0001", { type: "reassign", to: "mem_TEST01" }), {
    assigneeId: "mem_TEST01",
  });
  assert.deepEqual(patchForAction(project, "task_LINK0001", { type: "lower_importance" }), {
    importance: "medium",
  });
  assert.deepEqual(patchForAction(project, "task_LINK0001", { type: "reschedule", to: "2026-05-24" }), {
    dueDate: "2026-05-24",
  });
  assert.deepEqual(patchForAction(project, "task_LINK0001", { type: "reschedule", to: "2026-05-24T18:00:00+09:00" }), {
    dueDate: "2026-05-24",
  });
  assert.deepEqual(patchForAction(project, "task_LINK0001", { type: "reschedule" }), {});
  assert.notEqual(
    localProjectFingerprint(project),
    localProjectFingerprint({
      ...project,
      tasks: [{ ...project.tasks[0], progress: 25 }],
    }),
  );
  assert.notEqual(
    localProjectFingerprint(project),
    localProjectFingerprint({
      ...project,
      goal: "Changed goal should mark analysis stale",
    }),
  );
  assert.equal(isProjectAnalysisStale(project, localProjectFingerprint(project)), false);
  assert.equal(
    isProjectAnalysisStale(
      {
        ...project,
        tasks: [{ ...project.tasks[0], progress: 25 }],
      },
      localProjectFingerprint(project),
    ),
    true,
  );

  const mapped = mapAnalyze(project, {
    snapshot_hash: "hash_analyze",
    priority: {
      tasks_priority: [
        {
          task_id: "task_LINK0001",
          rank: 1,
          score: 87,
          factors: {
            deadline_pressure: 0.9,
            importance: 0.75,
            predecessor_pressure: 0.2,
            progress_gap: 1,
            overload_penalty: 0,
          },
          evidence_facts: ["마감까지 3일"],
          rationale: "마감까지 3일이라 먼저 확인합니다.",
        },
      ],
      task_decompositions: [
        {
          source_task_id: "task_LINK0001",
          decomposition_confidence: 0.82,
          subtasks: [{ title: "API 계약 확인", description: "응답 필드 확인", estimated_hours_range: [1, 2] }],
        },
      ],
      task_assignments: [
        {
          task_id: "task_LINK0001",
          assignee_id: "mem_TEST01",
          rationale_facts: ["role_hint=none", "member role=Engineer"],
          rationale: "부하가 가장 낮은 담당자에게 배정했습니다.",
        },
      ],
    },
    schedule: {
      slot_proposals: [
        {
          task_id: "task_LINK0001",
          selected_index: 0,
          rerank_rationale: "오전 집중 시간과 맞습니다.",
          rerank_source: "llm_reranked",
          candidate_slots: [
            {
              starts_at: "2026-05-18T00:30:00+09:00",
              ends_at: "2026-05-18T02:30:00+09:00",
              quality: "preferred",
              fit_score: 91,
              conflicts: [{ event_id: "evt_BUSY", kind: "soft_overlap" }],
            },
          ],
        },
      ],
      unschedulable: [{ task_id: "task_NOCAP001", reasons: ["no_capacity_before_deadline", "missing_assignee"] }],
    },
    risk: {
      checks: [
        {
          id: "workload_concentration",
          group: "workload",
          label: "담당자 업무 쏠림",
          result: "fail",
          is_blocker: false,
          evidence_facts: ["critical task 미배정"],
        },
      ],
      task_risk_levels: [{ task_id: "task_LINK0001", level: "at_risk" }],
      suggestions: [
        {
          id: "rs_workloadconcentration0000",
          fixes_check_ids: ["workload_concentration"],
          action: { type: "reassign", target_task_id: "task_LINK0001", to: "mem_TEST01" },
          rationale_facts: ["담당자 지정 필요"],
          user_facing_text: "담당자 지정이 필요합니다.",
        },
      ],
      soft_checks: [
        {
          id: "S1",
          trigger_label: "implicit_dependency_suspected",
          confidence: 0.77,
          involved_task_ids: ["task_LINK0001"],
          supporting_facts: ["API 계약 확인 필요"],
          user_facing_text: "암묵적 의존을 PM이 확인해야 합니다.",
          suggested_action: { type: "add_predecessor", target_task_id: "task_LINK0001", to: "task_API00001" },
        },
      ],
      member_workload: [{ member_id: "mem_TEST01", scheduled_hours_next_7d: 4, utilization: 0.5 }],
      blockers_failed: [],
      summary: "critical task 미배정 1건",
    },
    meta: {
      llm_fallbacks: {
        schedule_rerank_violation: true,
        risk_soft_checks_timeout: false,
        narrator_fallback_template: true,
        priority_narrator_fallback: true,
        risk_narrator_fallback: false,
      },
    },
  });

  assert.equal(mapped.snapshotHash, "hash_analyze");
  assert.equal(mapped.priority[0].factors.deadline, 0.9);
  assert.equal(mapped.taskAssignments[0].assigneeId, "mem_TEST01");
  assert.equal(mapped.decompositions[0].subtasks[0].estimated_hours_range[1], 2);
  assert.equal(mapped.schedule.proposals[0].candidateSlots[0].rerankSource, "llm_reranked");
  assert.equal(mapped.schedule.proposals[0].candidateSlots[0].rerankRationale, "오전 집중 시간과 맞습니다.");
  assert.equal(mapped.schedule.proposals[0].candidateSlots[0].date, "2026-05-18");
  assert.equal(mapped.schedule.proposals[0].candidateSlots[0].startTime, "00:30");
  assert.deepEqual(mapped.schedule.proposals[0].candidateSlots[0].conflicts, ["soft_overlap:evt_BUSY"]);
  assert.equal(mapped.schedule.unschedulable[0].reason, "no_capacity_before_deadline, missing_assignee");
  assert.equal(mapped.risk.checks[0].status, "fail");
  assert.deepEqual(mapped.risk.suggestions[0].patch, { assigneeId: "mem_TEST01" });
  assert.deepEqual(mapped.risk.suggestions[0].fixesCheckIds, ["workload_concentration"]);
  assert.equal(mapped.risk.suggestions[0].targetMemberId, "mem_TEST01");
  assert.equal(mapped.risk.suggestions[0].targetMemberName, "Backend");
  assert.deepEqual(mapped.risk.softChecks[0].patch, { predecessorIds: ["task_API00001"] });
  assert.equal(mapped.risk.memberWorkload[0].assignedHours, 4);
  assert.deepEqual(mapped.meta.llmFallbacks, {
    scheduleRerankViolation: true,
    riskSoftChecksTimeout: false,
    narratorFallbackTemplate: true,
    priorityNarratorFallback: true,
    riskNarratorFallback: false,
  });

  const parsedExport = parseExportPayload(JSON.stringify({ schemaVersion: 1, currentUser: null, projects: [project] }));
  assert.equal(parsedExport.schemaVersion, 1);
  assert.equal(parsedExport.projects[0].tasks[0].status, "todo");
  const demoExportText = await readFile(new URL("../../demos/local-demo-export.json", import.meta.url), "utf8");
  const demoExport = parseExportPayload(demoExportText);
  assert.equal(demoExport.projects[0].id, "proj_DEMO0001");
  assert.ok(demoExport.projects[0].tasks.length >= 4);
  assert.ok(demoExport.projects[0].events.some((event) => event.approved));
  const parsedWithAnalysis = parseExportPayload(
    JSON.stringify({
      schemaVersion: 1,
      currentUser: null,
      projects: [{ ...project, lastAnalysis: mapped, lastAnalysisFingerprint: localProjectFingerprint(project) }],
    }),
  );
  assert.equal(parsedWithAnalysis.projects[0].lastAnalysis.snapshotHash, "hash_analyze");
  assert.equal(parsedWithAnalysis.projects[0].lastAnalysisFingerprint, localProjectFingerprint(project));
  const parsedWithInvalidAnalysis = parseExportPayload(
    JSON.stringify({
      schemaVersion: 1,
      currentUser: null,
      projects: [{ ...project, lastAnalysis: { schedule: null }, lastAnalysisFingerprint: "bad" }],
    }),
  );
  assert.equal(parsedWithInvalidAnalysis.projects[0].lastAnalysis, undefined);
  assert.equal(parsedWithInvalidAnalysis.projects[0].lastAnalysisFingerprint, undefined);
  assert.match(mintId("proj"), /^proj_[a-z0-9]{8}$/);
  assert.match(mintId("mem"), /^mem_[a-z0-9]{8}$/);
  assert.match(mintId("task"), /^task_[a-z0-9]{8}$/);
  assert.match(mintId("ms"), /^ms_[a-z0-9]{8}$/);
  assert.throws(
    () => parseExportPayload(JSON.stringify({ schemaVersion: 1, currentUser: null, projects: [] }), MAX_EXPORT_BYTES + 1),
    /3MB 이하/,
  );
  assert.throws(
    () => parseExportPayload(JSON.stringify({ schemaVersion: 2, currentUser: null, projects: [] })),
    /지원하지 않는 export 파일/,
  );
  assert.throws(
    () =>
      parseExportPayload(
        JSON.stringify({
          schemaVersion: 1,
          currentUser: null,
          projects: [{ ...project, id: "proj_bad", members: [{ ...project.members[0], id: "mem_bad" }] }],
        }),
      ),
    /백엔드 계약에 맞지 않는 ID/,
  );
  assert.deepEqual(
    taskInfoFieldsFromError(
      new ApiError("Task 필수 정보를 입력해 주세요.", "task_info_insufficient", {
        fields: ["title", "importance", "estimated_hours", "deadline"],
      }),
    ),
    ["title", "importance", "estimatedHours", "dueDate"],
  );
  assert.deepEqual(taskInfoFieldsFromError(new ApiError("다른 오류", "validation_error", {})), []);
  assert.equal(userFacingApiError(new ApiError("rate", "rate_limited")), "잠시 후 다시 시도해 주세요.");
  assert.equal(userFacingApiError(new ApiError("agent", "agent_failed")), "AI 분석 일부가 실패했습니다. 다시 시도해 주세요.");
  assert.equal(userFacingApiError(new ApiError("network", "network_error")), "네트워크 오류입니다. 마지막 분석 결과를 표시 중입니다.");
  assert.equal(
    userFacingApiError(new ApiError("cycle", "circular_dependency", { cycle_path: ["task_A", "task_B", "task_A"] })),
    "순환 의존이 있습니다: task_A → task_B → task_A",
  );

  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    return {
      ok: true,
      json: async () => ({
        events_created: [
          {
            event_id: "evt_CREATED1",
            task_id: "task_LINK0001",
            assignee_id: "mem_TEST01",
            starts_at: "2026-05-18T00:30:00+09:00",
            ends_at: "2026-05-18T02:30:00+09:00",
            approved: true,
            source: "ai_suggested",
          },
        ],
        events_rejected: [],
      }),
    };
  };
  try {
    await assert.rejects(
      () =>
        approveProjectSchedule(
          {
            ...project,
            tasks: [{ ...project.tasks[0], progress: 25 }],
          },
          {
            snapshotHash: "hash_123",
            schedule: {
              proposals: [
                {
                  taskId: "task_LINK0001",
                  selectedIndex: 0,
                  candidateSlots: [
                    { date: "2026-05-18", startTime: "09:00", endTime: "13:00", quality: "preferred", fitScore: 90, conflicts: [] },
                  ],
                },
              ],
              unschedulable: [],
            },
          },
          ["task_LINK0001"],
          localProjectFingerprint(project),
        ),
      /데이터가 변경되어 분석을 다시 실행/,
    );
    assert.equal(calls.length, 0);

    const approvalResult = await approveProjectSchedule(
      project,
      {
        snapshotHash: "hash_123",
        schedule: {
          proposals: [
            {
              taskId: "task_LINK0001",
              selectedIndex: 1,
              overrideDate: "2026-05-18",
              overrideStartTime: "11:00",
              overrideEndTime: "15:00",
              candidateSlots: [
                { date: "2026-05-18", startTime: "09:00", endTime: "13:00", quality: "preferred", fitScore: 90, conflicts: [] },
                { date: "2026-05-18", startTime: "11:00", endTime: "15:00", quality: "acceptable", fitScore: 80, conflicts: [] },
              ],
            },
          ],
          unschedulable: [],
        },
      },
      ["task_LINK0001"],
      localProjectFingerprint(project),
    );

    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "http://127.0.0.1:8000/v1/projects/proj_TEST0001/schedule:approve");
    assert.deepEqual(JSON.parse(calls[0].init.body), {
      snapshot_hash: "hash_123",
      approvals: [
        {
          task_id: "task_LINK0001",
          candidate_slot_index: 1,
          override_starts_at: "2026-05-18T11:00:00+09:00",
          override_ends_at: "2026-05-18T15:00:00+09:00",
        },
      ],
    });
    assert.equal(approvalResult.project.events[0].id, "evt_CREATED1");
    assert.equal(approvalResult.project.events[0].date, "2026-05-18");
  assert.equal(approvalResult.project.events[0].startTime, "00:30");
    assert.equal(approvalResult.project.lastSnapshotHash, "hash_123");
  } finally {
    globalThis.fetch = originalFetch;
  }

  const newProjectSource = await readFile(new URL("../src/app/pages/NewProject.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(newProjectSource, /Backend fallback/);
  assert.doesNotMatch(newProjectSource, /catch\s*(?:\([^)]*\))?\s*\{[^}]*addProject\(localProject\)/s);
  assert.doesNotMatch(newProjectSource, /finally\s*\{[^}]*setStep\(3\)/s);

  const dashboardSource = await readFile(new URL("../src/app/pages/Dashboard.tsx", import.meta.url), "utf8");
  const routesSource = await readFile(new URL("../src/app/routes.tsx", import.meta.url), "utf8");
  const storeSource = await readFile(new URL("../src/app/store.tsx", import.meta.url), "utf8");
  const schemasSource = await readFile(new URL("../src/app/schemas.ts", import.meta.url), "utf8");
  const packageJson = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
  const rootPackageJson = JSON.parse(await readFile(new URL("../../package.json", import.meta.url), "utf8"));
  const rootReadmeSource = await readFile(new URL("../../README.md", import.meta.url), "utf8");
  const bundleBudgetSource = await readFile(new URL("../../scripts/check_fe_bundle_budget.mjs", import.meta.url), "utf8");
  const openApiCheckSource = await readFile(new URL("../../scripts/check_openapi_generated.py", import.meta.url), "utf8");
  const playwrightSmokeSource = await readFile(new URL("./local-smoke.spec.ts", import.meta.url), "utf8");
  const verificationRunbookSource = await readFile(new URL("../../docs/local-verification-runbook.md", import.meta.url), "utf8");
  assert.ok(packageJson.dependencies?.zod);
  assert.equal(packageJson.scripts?.["check:e2e-list"], "playwright test tests/local-smoke.spec.ts --list");
  assert.match(rootPackageJson.scripts?.["dev:fe"] ?? "", /VITE_API_BASE_URL=http:\/\/127\.0\.0\.1:8000/);
  assert.match(rootPackageJson.scripts?.["dev:fe"] ?? "", /--port 5173/);
  assert.match(rootPackageJson.scripts?.["dev:be"] ?? "", /--port 8000/);
  assert.match(rootPackageJson.scripts?.["smoke:local"] ?? "", /http:\/\/127\.0\.0\.1:8000/);
  assert.equal(rootPackageJson.scripts?.["qa:local"], "bash scripts/run_local_quality_checks.sh");
  assert.equal(rootPackageJson.scripts?.["check:audit"], "BE/.venv/bin/python scripts/check_audit_consistency.py");
  assert.equal(rootPackageJson.scripts?.["check:local-servers"], "BE/.venv/bin/python scripts/check_local_servers.py");
  assert.equal(rootPackageJson.scripts?.["check:upstage-ready"], "PYTHONPATH=BE BE/.venv/bin/python scripts/check_upstage_readiness.py");
  assert.equal(rootPackageJson.scripts?.["check:completion"], "bash scripts/check_completion_ready.sh");
  assert.equal(rootPackageJson.scripts?.["check:e2e-list"], "npm --workspace FE run check:e2e-list");
  assert.equal(rootPackageJson.scripts?.["check:fe-bundle"], "node scripts/check_fe_bundle_budget.mjs");
  assert.equal(rootPackageJson.scripts?.["check:openapi"], "PYTHONPATH=BE BE/.venv/bin/python scripts/check_openapi_generated.py");
  assert.match(rootReadmeSource, /http:\/\/127\.0\.0\.1:5173\//);
  assert.match(rootReadmeSource, /http:\/\/127\.0\.0\.1:8000/);
  assert.match(rootReadmeSource, /UPSTAGE_API_KEY/);
  assert.match(rootReadmeSource, /npm run qa:local/);
  assert.match(rootReadmeSource, /npm run check:completion/);
  assert.match(rootReadmeSource, /completed successfully/);
  const qaLocalSource = await readFile(new URL("../../scripts/run_local_quality_checks.sh", import.meta.url), "utf8");
  const auditCheckSource = await readFile(new URL("../../scripts/check_audit_consistency.py", import.meta.url), "utf8");
  const localServersSource = await readFile(new URL("../../scripts/check_local_servers.py", import.meta.url), "utf8");
  const completionCheckSource = await readFile(new URL("../../scripts/check_completion_ready.sh", import.meta.url), "utf8");
  const upstageReadinessSource = await readFile(new URL("../../scripts/check_upstage_readiness.py", import.meta.url), "utf8");
  assert.match(completionCheckSource, /npm run qa:local/);
  assert.match(completionCheckSource, /--require-key --live/);
  assert.match(completionCheckSource, /npm run test:e2e/);
  assert.match(qaLocalSource, /npm run check:openapi/);
  assert.match(qaLocalSource, /npm run check:upstage-ready/);
  assert.match(qaLocalSource, /npm run test:be/);
  assert.match(qaLocalSource, /npm run test:fe/);
  assert.match(qaLocalSource, /npm run build:fe/);
  assert.match(qaLocalSource, /npm run check:fe-bundle/);
  assert.match(qaLocalSource, /npm run check:e2e-list/);
  assert.match(qaLocalSource, /npm run check:local-servers/);
  assert.match(qaLocalSource, /npm run check:audit/);
  assert.match(qaLocalSource, /SMOKE_BASE_URL="\$\{SMOKE_BASE_URL:-http:\/\/127\.0\.0\.1:8000\}" npm run smoke:local/);
  assert.match(qaLocalSource, /git diff --check/);
  assert.match(bundleBudgetSource, /BUNDLE_GZIP_BUDGET_BYTES/);
  assert.match(bundleBudgetSource, /300 \* 1024/);
  assert.match(openApiCheckSource, /OpenAPI generated client is stale/);
  assert.match(auditCheckSource, /Review Cycle Log/);
  assert.match(auditCheckSource, /Known Gaps/);
  assert.match(auditCheckSource, /Completion Evidence/);
  assert.match(auditCheckSource, /Prompt-to-Artifact Checklist/);
  assert.match(auditCheckSource, /DONE_CRITERIA_TOKENS/);
  assert.match(auditCheckSource, /local-verification-runbook/);
  assert.match(auditCheckSource, /README\.md/);
  assert.match(auditCheckSource, /Root README must include local handoff token/);
  assert.match(auditCheckSource, /npm run check:completion/);
  assert.match(auditCheckSource, /Final completion command/);
  assert.match(auditCheckSource, /No unresolved gaps/);
  assert.match(auditCheckSource, /Schema Pass Rate/);
  assert.match(auditCheckSource, /Latency P95/);
  assert.match(auditCheckSource, /발표 데모/);
  assert.match(localServersSource, /FE_BASE_URL/);
  assert.match(localServersSource, /BE_BASE_URL/);
  assert.match(localServersSource, /262144/);
  assert.match(localServersSource, /http:\/\/127\.0\.0\.1:5173\//);
  assert.match(localServersSource, /http:\/\/127\.0\.0\.1:8000/);
  assert.match(localServersSource, /\/v1\/health/);
  assert.match(localServersSource, /\/openapi\.json/);
  assert.match(localServersSource, /score_action_coherence/);
  assert.match(localServersSource, /frontend_api_client_module/);
  assert.match(localServersSource, /src\/app\/apiClient\.ts/);
  assert.match(localServersSource, /has_current_backend/);
  assert.match(localServersSource, /has_stale_8014/);
  assert.match(localServersSource, /frontend_dashboard_module/);
  assert.match(localServersSource, /src\/app\/pages\/Dashboard\.tsx/);
  assert.match(localServersSource, /has_stale_calendar_update/);
  assert.match(localServersSource, /moveCalendarEventAndReanalyze/);
  assert.match(localServersSource, /cors_preflight/);
  assert.match(localServersSource, /CHECK_ALLOWED_ORIGIN/);
  assert.match(localServersSource, /CHECK_REJECTED_ORIGIN/);
  assert.match(localServersSource, /access-control-allow-origin/);
  assert.match(upstageReadinessSource, /upstage_readiness_probe/);
  assert.match(upstageReadinessSource, /--live/);
  assert.match(upstageReadinessSource, /--require-key/);
  assert.match(playwrightSmokeSource, /http:\/\/127\.0\.0\.1:5173\//);
  assert.match(playwrightSmokeSource, /http:\/\/127\.0\.0\.1:8000/);
  assert.match(playwrightSmokeSource, /use_llm: false/);
  assert.doesNotMatch(playwrightSmokeSource, /http:\/\/127\.0\.0\.1:5192\//);
  assert.doesNotMatch(playwrightSmokeSource, /http:\/\/127\.0\.0\.1:8013/);
  assert.doesNotMatch(playwrightSmokeSource, /http:\/\/127\.0\.0\.1:8014/);
  assert.doesNotMatch(playwrightSmokeSource, /http:\/\/127\.0\.0\.1:5174\//);
  assert.doesNotMatch(playwrightSmokeSource, /http:\/\/127\.0\.0\.1:8002/);
  assert.match(playwrightSmokeSource, /scenario 1 normal project/);
  assert.match(playwrightSmokeSource, /scenario 2 unschedulable task/);
  assert.match(playwrightSmokeSource, /scenario 3 overload and unassigned/);
  assert.match(playwrightSmokeSource, /scenario 4 circular dependency/);
  assert.match(playwrightSmokeSource, /scenario 5 stale schedule approval/);
  assert.match(verificationRunbookSource, /npm run qa:local/);
  assert.match(verificationRunbookSource, /npm run test:e2e/);
  assert.match(verificationRunbookSource, /--require-key --live/);
  assert.match(verificationRunbookSource, /UPSTAGE_API_KEY/);
  assert.match(verificationRunbookSource, /update_goal/);
  assert.match(schemasSource, /from "zod"/);
  assert.match(schemasSource, /localStoreEnvelopeSchema/);
  assert.match(schemasSource, /taskDraftSchema/);
  assert.match(storeSource, /localStoreEnvelopeSchema/);
  assert.match(storeSource, /lastAnalysis/);
  assert.match(storeSource, /lastAnalysisFingerprint/);
  assert.match(dashboardSource, /useForm/);
  assert.match(dashboardSource, /handleSubmit/);
  assert.match(dashboardSource, /taskDraftSchema/);
  assert.match(dashboardSource, /safeParse\(draftTask\)/);
  assert.match(dashboardSource, /aria-label="Task 데드라인"/);
  assert.match(dashboardSource, /function TaskField/);
  assert.match(dashboardSource, /h-4 truncate whitespace-nowrap text-xs leading-4 text-neutral-500/);
  assert.match(dashboardSource, /grid grid-cols-1 gap-2 sm:grid-cols-2/);
  assert.doesNotMatch(dashboardSource, /label="Task 이름" hint="작업명"/);
  assert.doesNotMatch(dashboardSource, /label="설명 \/ 완료 조건" hint="필요한 경우 작성"/);
  assert.match(dashboardSource, /label="중요도"/);
  assert.match(dashboardSource, /label="상태"/);
  assert.match(dashboardSource, /label="담당자"/);
  assert.doesNotMatch(dashboardSource, /PM 조치/);
  assert.match(dashboardSource, /AI 제안/);
  assert.match(dashboardSource, /suggestion\.summary/);
  assert.match(dashboardSource, /unschedulablePmAction/);
  assert.match(dashboardSource, /riskCheckLabels/);
  assert.match(dashboardSource, /대상 Task/);
  assert.match(dashboardSource, /suggestionTask\.title/);
  assert.match(dashboardSource, /마감일 변경안을 리스크 탭에서 적용하세요/);
  assert.match(dashboardSource, /선행 관계에서/);
  assert.doesNotMatch(dashboardSource, /일정 재조정 제안을 확인하세요/);
  assert.match(dashboardSource, /fixesCheckIds/);
  assert.match(dashboardSource, /suggestion\.targetMemberName/);
  assert.match(dashboardSource, /로 담당자 지정/);
  assert.match(dashboardSource, /label="마일스톤"/);
  assert.match(dashboardSource, /label="데드라인"/);
  assert.match(dashboardSource, /label="예상 시간"/);
  assert.doesNotMatch(dashboardSource, /label="지연 사유" hint="지연 시 작성"/);
  assert.match(dashboardSource, /label="선행 Task"/);
  assert.match(dashboardSource, /label="진척률"/);
  assert.doesNotMatch(dashboardSource, /hint="/);
  assert.doesNotMatch(dashboardSource, /label="마감일"/);
  assert.doesNotMatch(dashboardSource, /Risk Agent가 확인/);
  assert.match(dashboardSource, /project\.lastAnalysis/);
  assert.match(dashboardSource, /lastAnalysisFingerprint/);
  assert.match(dashboardSource, /dropImportedAnalysis/);
  assert.match(dashboardSource, /lastAnalysisFingerprint: undefined/);
  assert.match(routesSource, /path: "projects"/);
  assert.match(routesSource, /path: "projects\/:projectId"/);
  assert.match(routesSource, /path: "projects\/:projectId\/setup"/);
  assert.match(routesSource, /path: "projects\/:projectId\/tasks"/);
  assert.match(routesSource, /path: "projects\/:projectId\/calendar"/);
  assert.match(routesSource, /path: "projects\/:projectId\/settings"/);
  assert.match(dashboardSource, /useParams/);
  assert.match(dashboardSource, /projectId/);
  assert.match(dashboardSource, /우선순위 개선/);
  assert.match(dashboardSource, /수동 조정 필요/);
  assert.match(dashboardSource, /hasApplicablePatch/);
  assert.match(dashboardSource, /Object\.keys\(suggestion\.patch\)\.length > 0/);
  assert.match(dashboardSource, /recordAnalyzeLatency/);
  assert.match(dashboardSource, /recordSuggestionAcceptance/);
  assert.match(dashboardSource, /role="grid"/);
  assert.match(dashboardSource, /onKeyDown/);
  assert.match(dashboardSource, /draggedEventId/);
  assert.match(dashboardSource, /draggable/);
  assert.match(dashboardSource, /onDragStart/);
  assert.match(dashboardSource, /onDrop/);
  assert.match(dashboardSource, /onMoveEvent\(draggedEventId, \{ date \}\)/);
  assert.match(dashboardSource, /const updateCalendarEvent =/);
  assert.match(dashboardSource, /const moveCalendarEventAndReanalyze =/);
  assert.match(dashboardSource, /onUpdateEvent=\{updateCalendarEvent\}/);
  assert.match(dashboardSource, /onMoveEvent=\{moveCalendarEventAndReanalyze\}/);
  assert.match(dashboardSource, /드래그해서 날짜를 변경하면 재분석됩니다/);
  assert.match(dashboardSource, /ArrowRight/);
  assert.match(dashboardSource, /ArrowLeft/);
  assert.match(dashboardSource, /ArrowDown/);
  assert.match(dashboardSource, /ArrowUp/);
  assert.match(dashboardSource, /qualityClass/);
  assert.match(dashboardSource, /acceptable/);
  assert.match(dashboardSource, /bg-amber-50/);
  assert.match(dashboardSource, /fallback/);
  assert.match(dashboardSource, /bg-orange-50/);
  assert.match(dashboardSource, /selectedDecompositionIds/);
  assert.match(dashboardSource, /선택 Task 분해 요청/);
  assert.match(dashboardSource, /Task로 추가 \[G3\]/);
  assert.match(dashboardSource, /id: mintId\("task"\)/);
  assert.match(dashboardSource, /type="checkbox"/);
  assert.match(dashboardSource, /fallbackBadges/);
  assert.match(dashboardSource, /일정 추천 검토 필요/);
  assert.match(dashboardSource, /리스크 확인 지연/);
  assert.doesNotMatch(dashboardSource, /LLM fallback/);
  assert.doesNotMatch(dashboardSource, /Narrator fallback/);
  assert.doesNotMatch(dashboardSource, /Priority narrator fallback/);
  assert.doesNotMatch(dashboardSource, /Risk narrator fallback/);
  const apiClientSource = await readFile(new URL("../src/app/apiClient.ts", import.meta.url), "utf8");
  const analysisTypesSource = await readFile(new URL("../src/app/analysisTypes.ts", import.meta.url), "utf8");
  const generatedOpenApiSource = await readFile(new URL("../src/app/generated/openapi.ts", import.meta.url), "utf8");
  assert.match(apiClientSource, /AnalyzeResponse as BackendAnalyzeResponse/);
  assert.match(apiClientSource, /MilestoneSuggestResponse as BackendMilestoneSuggestResponse/);
  assert.match(apiClientSource, /MilestoneApproveResponse as BackendMilestoneApproveResponse/);
  assert.match(apiClientSource, /ApproveScheduleResponse as BackendApproveScheduleResponse/);
  assert.match(apiClientSource, /RiskSimulateResponse as BackendRiskSimulateResponse/);
  assert.match(apiClientSource, /openApiPaths/);
  assert.match(generatedOpenApiSource, /export const openApiPaths/);
  assert.match(generatedOpenApiSource, /createProject/);
  assert.match(generatedOpenApiSource, /suggestMilestones/);
  assert.match(generatedOpenApiSource, /approveSchedule/);
  assert.match(generatedOpenApiSource, /simulateRisk/);
  assert.doesNotMatch(apiClientSource, /apiRequest<\{\s*project_id: string\s*\}>/s);
  assert.doesNotMatch(apiClientSource, /apiRequest<\{\s*proposed_milestones:/s);
  assert.doesNotMatch(apiClientSource, /apiRequest<\{\s*events_created:/s);
  assert.match(generatedOpenApiSource, /Generated from FastAPI OpenAPI schema/);
  assert.match(generatedOpenApiSource, /export type AnalyzeResponse =/);
  assert.match(generatedOpenApiSource, /export type TaskDecompositionSubtask =/);
  assert.doesNotMatch(apiClientSource, /estimated_hours_range\?:/);
  assert.doesNotMatch(analysisTypesSource, /estimated_hours_range\?:/);
} finally {
  await server.close();
}
