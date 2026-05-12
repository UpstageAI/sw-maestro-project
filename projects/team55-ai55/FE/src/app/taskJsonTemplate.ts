import { mintId, type ImportanceLevel, type Project, type Task, type TaskStatus } from "./store";

const MAX_TASK_TEMPLATE_BYTES = 128 * 1024;
const IMPORTANCE_VALUES = new Set<ImportanceLevel>(["low", "medium", "high", "critical"]);
const STATUS_VALUES = new Set<TaskStatus>(["todo", "in_progress", "blocked", "review", "done", "cancelled"]);

type TemplateResult = {
  task: Task;
  warnings: string[];
};

type TemplatesResult = {
  tasks: Task[];
  warnings: string[];
};

type TaskTemplateObject = Record<string, unknown>;

export function applyTaskJsonTemplate(project: Project, currentTask: Task, text: string, byteSize = new Blob([text]).size): TemplateResult {
  const payload = parseTemplatePayload(text, byteSize);
  const template = pickTemplateObject(payload);
  const warnings: string[] = [];
  return {
    task: buildTaskFromTemplate(project, currentTask, template, warnings, true),
    warnings,
  };
}

export function applyTaskJsonTemplates(
  project: Project,
  currentTask: Task,
  text: string,
  byteSize = new Blob([text]).size,
  idFactory: () => string = () => mintId("task"),
): TemplatesResult {
  const payload = parseTemplatePayload(text, byteSize);
  const templates = pickTemplateObjects(payload);
  if (templates.length === 0) {
    throw new Error("Task JSON에 tasks 항목이 필요합니다.");
  }

  const warnings: string[] = [];
  const tasks = templates.map((template) =>
    buildTaskFromTemplate(project, createImportBaseTask(currentTask, idFactory()), template, warnings, false),
  );
  const titleToTask = new Map<string, Task>();
  for (const task of [...project.tasks, ...tasks]) {
    if (!titleToTask.has(normalized(task.title))) {
      titleToTask.set(normalized(task.title), task);
    }
  }
  const idToTask = new Map([...project.tasks, ...tasks].map((task) => [task.id, task]));

  return {
    tasks: tasks.map((task, index) => ({
      ...task,
      predecessorIds: resolvePredecessorIdsFromTaskSet(
        idToTask,
        titleToTask,
        task.id,
        templates[index],
        warnings,
      ),
    })),
    warnings,
  };
}

function parseTemplatePayload(text: string, byteSize: number): unknown {
  if (byteSize > MAX_TASK_TEMPLATE_BYTES) {
    throw new Error("Task JSON 템플릿은 128KB 이하만 사용할 수 있습니다.");
  }

  try {
    return JSON.parse(text);
  } catch {
    throw new Error("올바른 JSON 파일이 아닙니다.");
  }
}

function pickTemplateObject(payload: unknown): TaskTemplateObject {
  if (Array.isArray(payload)) {
    return objectValue(payload[0]);
  }
  const root = objectValue(payload);
  const nestedTask = objectValue(root.task, false);
  if (nestedTask) return nestedTask;
  const nestedTasks = Array.isArray(root.tasks) ? objectValue(root.tasks[0], false) : null;
  return nestedTasks ?? root;
}

function pickTemplateObjects(payload: unknown): TaskTemplateObject[] {
  if (Array.isArray(payload)) {
    return payload.map((item) => objectValue(item));
  }
  const root = objectValue(payload);
  if (Array.isArray(root.tasks)) {
    return root.tasks.map((item) => objectValue(item));
  }
  const nestedTask = objectValue(root.task, false);
  return [nestedTask ?? root];
}

function objectValue(value: unknown, throwOnInvalid?: true): TaskTemplateObject;
function objectValue(value: unknown, throwOnInvalid: false): TaskTemplateObject | null;
function objectValue(value: unknown, throwOnInvalid = true): TaskTemplateObject | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as TaskTemplateObject;
  }
  if (throwOnInvalid) {
    throw new Error("Task JSON은 객체이거나 첫 번째 항목이 Task 객체인 배열이어야 합니다.");
  }
  return null;
}

function buildTaskFromTemplate(
  project: Project,
  currentTask: Task,
  template: TaskTemplateObject,
  warnings: string[],
  resolvePredecessors: boolean,
): Task {
  const title = stringValue(template.title);
  if (!title) {
    throw new Error("Task JSON에 title이 필요합니다.");
  }
  const assigneeId = resolveMemberId(project, template, warnings) ?? currentTask.assigneeId ?? null;
  const milestoneId = resolveMilestoneId(project, template, warnings) ?? currentTask.milestoneId ?? null;
  const predecessorIds = resolvePredecessors ? resolvePredecessorIds(project, currentTask.id, template, warnings) : [];

  return {
    ...currentTask,
    title,
    description: stringValue(template.description) ?? currentTask.description,
    importance: enumValue(template.importance, IMPORTANCE_VALUES, currentTask.importance, "importance", warnings),
    status: enumValue(template.status, STATUS_VALUES, currentTask.status, "status", warnings),
    assigneeId,
    milestoneId,
    dueDate: dateValue(template.dueDate, currentTask.dueDate, warnings),
    estimatedHours: positiveNumberValue(template.estimatedHours, currentTask.estimatedHours ?? 4, "estimatedHours", warnings),
    progress: progressValue(template.progress, currentTask.progress, warnings),
    predecessorIds,
    delayReason: nullableStringValue(template.delayReason, currentTask.delayReason),
  };
}

function createImportBaseTask(currentTask: Task, id: string): Task {
  return {
    ...currentTask,
    id,
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

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function nullableStringValue(value: unknown, fallback: string | null | undefined): string | null {
  if (value === null) return null;
  return stringValue(value) ?? fallback ?? null;
}

function enumValue<T extends string>(value: unknown, allowed: Set<T>, fallback: T, field: string, warnings: string[]): T {
  if (typeof value !== "string" || value.trim() === "") return fallback;
  const normalized = value.trim();
  if (allowed.has(normalized as T)) return normalized as T;
  warnings.push(`${field} 값이 지원되지 않아 기존 값을 유지했습니다.`);
  return fallback;
}

function positiveNumberValue(value: unknown, fallback: number | null, field: string, warnings: string[]): number | null {
  if (value === null) return null;
  if (value === undefined || value === "") return fallback;
  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(numeric) && numeric > 0) return numeric;
  warnings.push(`${field} 값이 양수가 아니라 기존 값을 유지했습니다.`);
  return fallback;
}

function progressValue(value: unknown, fallback: number, warnings: string[]): number {
  if (value === undefined || value === "") return fallback;
  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(numeric)) return Math.max(0, Math.min(100, Math.round(numeric)));
  warnings.push("progress 값이 숫자가 아니라 기존 값을 유지했습니다.");
  return fallback;
}

function dateValue(value: unknown, fallback: string | null | undefined, warnings: string[]): string | null {
  if (value === null) return null;
  if (value === undefined || value === "") return fallback ?? null;
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value.trim())) return value.trim();
  warnings.push("dueDate는 YYYY-MM-DD 형식이어야 해서 기존 값을 유지했습니다.");
  return fallback ?? null;
}

function resolveMemberId(project: Project, template: TaskTemplateObject, warnings: string[]): string | null {
  const assigneeId = stringValue(template.assigneeId);
  if (assigneeId) {
    if (project.members.some((member) => member.id === assigneeId)) return assigneeId;
    warnings.push("assigneeId와 일치하는 담당자가 없어 기존 담당자를 유지했습니다.");
    return null;
  }

  const assigneeName = stringValue(template.assigneeName);
  if (!assigneeName) return null;
  const member = project.members.find((candidate) => normalized(candidate.name) === normalized(assigneeName));
  if (member) return member.id;
  warnings.push("assigneeName과 일치하는 담당자가 없어 기존 담당자를 유지했습니다.");
  return null;
}

function resolveMilestoneId(project: Project, template: TaskTemplateObject, warnings: string[]): string | null {
  const milestoneId = stringValue(template.milestoneId);
  if (milestoneId) {
    if (project.milestones.some((milestone) => milestone.id === milestoneId)) return milestoneId;
    warnings.push("milestoneId와 일치하는 마일스톤이 없어 기존 마일스톤을 유지했습니다.");
    return null;
  }

  const milestoneTitle = stringValue(template.milestoneTitle);
  if (!milestoneTitle) return null;
  const milestone = project.milestones.find((candidate) => normalized(candidate.title) === normalized(milestoneTitle));
  if (milestone) return milestone.id;
  warnings.push("milestoneTitle과 일치하는 마일스톤이 없어 기존 마일스톤을 유지했습니다.");
  return null;
}

function resolvePredecessorIds(project: Project, currentTaskId: string, template: TaskTemplateObject, warnings: string[]): string[] {
  const ids = stringArray(template.predecessorIds);
  const titles = stringArray(template.predecessorTitles);
  const resolved = new Set<string>();

  for (const id of ids) {
    if (id !== currentTaskId && project.tasks.some((task) => task.id === id)) {
      resolved.add(id);
    } else {
      warnings.push(`선행 Task ID ${id}를 찾지 못해 제외했습니다.`);
    }
  }

  for (const title of titles) {
    const task = project.tasks.find((candidate) => candidate.id !== currentTaskId && normalized(candidate.title) === normalized(title));
    if (task) {
      resolved.add(task.id);
    } else {
      warnings.push(`선행 Task 제목 ${title}을 찾지 못해 제외했습니다.`);
    }
  }

  return [...resolved];
}

function resolvePredecessorIdsFromTaskSet(
  idToTask: Map<string, Task>,
  titleToTask: Map<string, Task>,
  currentTaskId: string,
  template: TaskTemplateObject,
  warnings: string[],
): string[] {
  const resolved = new Set<string>();
  for (const id of stringArray(template.predecessorIds)) {
    if (id !== currentTaskId && idToTask.has(id)) {
      resolved.add(id);
    } else {
      warnings.push(`선행 Task ID ${id}를 찾지 못해 제외했습니다.`);
    }
  }

  for (const title of stringArray(template.predecessorTitles)) {
    const task = titleToTask.get(normalized(title));
    if (task && task.id !== currentTaskId) {
      resolved.add(task.id);
    } else {
      warnings.push(`선행 Task 제목 ${title}을 찾지 못해 제외했습니다.`);
    }
  }

  return [...resolved];
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(stringValue).filter((item): item is string => Boolean(item)) : [];
}

function normalized(value: string): string {
  return value.trim().toLowerCase();
}
