import { expect, Page, test } from "@playwright/test";

const FE_BASE_URL = (process.env.E2E_FE_URL ?? "http://127.0.0.1:5173/").replace(/\/$/, "");
const BE_BASE_URL = process.env.E2E_BE_URL ?? "http://127.0.0.1:8000";
const STORAGE_KEY = "omc-pm-55:v1";

type SeedProject = {
  id: string;
  name: string;
  goal: string;
  startsAt: string;
  endsAt: string;
  baseHours: number;
  defaultWorkStart: string;
  defaultWorkEnd: string;
  weekendEnabled: boolean;
  weekendWorkStart: string;
  weekendWorkEnd: string;
  members: Array<{
    id: string;
    name: string;
    role: string;
    availableHours: number;
    workStart: string;
    workEnd: string;
  }>;
  milestones: Array<{ id: string; title: string; dueDate: string; status: "approved" }>;
  tasks: Array<{
    id: string;
    milestoneId: string | null;
    title: string;
    description: string;
    assigneeId: string | null;
    importance: "low" | "medium" | "high" | "critical";
    status: "todo" | "in_progress" | "blocked" | "review" | "done" | "cancelled";
    progress: number;
    estimatedHours: number;
    dueDate: string;
    predecessorIds: string[];
    delayReason: string | null;
  }>;
  events: Array<{
    id: string;
    taskId: string;
    title: string;
    date: string;
    assigneeId: string | null;
    startTime: string;
    endTime: string;
    approved: boolean;
    source: "ai_suggested" | "pm_manual" | "external_blocking";
  }>;
};

function baseProject(overrides: Partial<SeedProject> = {}): SeedProject {
  return {
    id: "proj_PLAY0001",
    name: "Playwright QA",
    goal: "FE/BE 로컬 통신과 Agent 산출물을 검증한다.",
    startsAt: "2026-05-07",
    endsAt: "2026-06-30",
    baseHours: 40,
    defaultWorkStart: "09:00",
    defaultWorkEnd: "18:00",
    weekendEnabled: false,
    weekendWorkStart: "10:00",
    weekendWorkEnd: "16:00",
    members: [
      {
        id: "mem_SMOKE1",
        name: "백엔드",
        role: "Backend",
        availableHours: 40,
        workStart: "09:00",
        workEnd: "18:00",
      },
    ],
    milestones: [{ id: "ms_SMOKE01", title: "MVP 검증", dueDate: "2026-05-30", status: "approved" }],
    tasks: [],
    events: [],
    ...overrides,
  };
}

function task(
  id: string,
  title: string,
  overrides: Partial<SeedProject["tasks"][number]> = {},
): SeedProject["tasks"][number] {
  return {
    id,
    milestoneId: "ms_SMOKE01",
    title,
    description: `${title} 완료 조건`,
    assigneeId: "mem_SMOKE1",
    importance: "high",
    status: "todo",
    progress: 0,
    estimatedHours: 4,
    dueDate: "2026-05-30",
    predecessorIds: [],
    delayReason: "검증용 입력",
    ...overrides,
  };
}

async function seedProject(page: Page, project: SeedProject) {
  await page.goto(`${FE_BASE_URL}/`, { waitUntil: "domcontentloaded" });
  await page.evaluate(
    ({ key, store }) => {
      localStorage.clear();
      localStorage.setItem(key, JSON.stringify(store));
    },
    {
      key: STORAGE_KEY,
      store: {
        schemaVersion: 1,
        currentUser: { name: "PM" },
        projects: [project],
        clientMetrics: { analyzeLatenciesMs: [], suggestionAcceptanceEvents: [] },
      },
    },
  );
  await page.goto(`${FE_BASE_URL}/projects/${project.id}`, { waitUntil: "networkidle" });
}

async function useDeterministicAnalyze(page: Page) {
  await page.route(`${BE_BASE_URL}/v1/projects/*/analyze`, async (route) => {
    const request = route.request();
    if (request.method() !== "POST") {
      await route.continue();
      return;
    }
    const payload = JSON.parse(request.postData() ?? "{}");
    await route.continue({
      postData: JSON.stringify({
        ...payload,
        options: {
          ...(payload.options ?? {}),
          use_llm: false,
        },
      }),
    });
  });
}

async function runAnalyze(page: Page) {
  const responsePromise = page.waitForResponse((response) =>
    response.url().startsWith(BE_BASE_URL) && response.url().includes("/analyze"),
  );
  await page.getByRole("button", { name: /AI 분석 다시 실행/ }).click();
  const response = await responsePromise;
  expect(response.ok()).toBeTruthy();
  await expect(page.getByText("Rank 1")).toBeVisible({ timeout: 7000 });
}

async function addTaskThroughForm(page: Page, title: string, memberLabel: string, dueDate: string) {
  await page.getByPlaceholder("Task 이름").fill(title);
  await page.getByPlaceholder("설명 / 완료 조건").fill(`${title} 완료 조건`);
  await page.locator("select").nth(2).selectOption({ label: memberLabel });
  await page.getByLabel("Task 데드라인").fill(dueDate);
  await page.getByRole("button", { name: /저장/ }).click();
  await expect(page.getByText(title).first()).toBeVisible();
}

test("scenario 1 normal project creates 5 tasks, analyzes, approves schedule, and renders calendar", async ({ page }) => {
  await useDeterministicAnalyze(page);
  const apiCalls: string[] = [];
  page.on("request", (request) => {
    if (request.url().startsWith(BE_BASE_URL)) {
      const url = new URL(request.url());
      apiCalls.push(`${request.method()} ${url.pathname}`);
    }
  });

  await page.goto(`${FE_BASE_URL}/`, { waitUntil: "networkidle" });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: "networkidle" });

  await page.getByLabel("이름").fill("PM");
  await page.getByRole("button", { name: "로그인" }).click();
  await page.getByRole("button", { name: "새 프로젝트 만들기" }).click();

  await page.getByPlaceholder("예: AI PM Assistant 웹 서비스").fill("정상 프로젝트");
  await page.getByPlaceholder("예: 4주 안에 MVP 런칭. 핵심 기능은 AI 일정 추천과 우선순위 분석.").fill("5 Task, 2 멤버, 빈 캘린더 E2E");
  await page.getByRole("button", { name: /다음/ }).click();

  for (const member of ["백엔드", "프론트"]) {
    await page.getByPlaceholder("홍길동").fill(member);
    await page.getByRole("button", { name: /추가/ }).click();
    await expect(page.getByText(member).last()).toBeVisible();
  }

  await page.getByRole("button", { name: /마일스톤 제안 받기/ }).click();
  await page.getByText("Agent 제안 마일스톤").waitFor();
  await page.getByRole("button", { name: "승인 및 프로젝트 생성" }).click();

  for (let index = 1; index <= 5; index += 1) {
    await addTaskThroughForm(page, `정상 Task ${index}`, index % 2 === 0 ? "프론트" : "백엔드", "2026-05-30");
  }

  await runAnalyze(page);
  await page.getByRole("button", { name: "일정안" }).click();
  const approveResponse = page.waitForResponse((response) =>
    response.url().startsWith(BE_BASE_URL) && response.url().includes("/schedule:approve"),
  );
  await page.getByRole("button", { name: /선택한 일정 승인/ }).click();
  expect((await approveResponse).ok()).toBeTruthy();
  await expect(page.getByText("내부 캘린더")).toBeVisible();
  await expect(page.getByText("정상 Task 1").last()).toBeVisible({ timeout: 7000 });

  expect(apiCalls.some((item) => item.includes("/milestones:suggest"))).toBeTruthy();
  expect(apiCalls.some((item) => item.includes("/analyze"))).toBeTruthy();
  expect(apiCalls.some((item) => item.includes("/schedule:approve"))).toBeTruthy();
});

test("scenario 2 unschedulable task shows no_capacity_before_deadline in Schedule tab", async ({ page }) => {
  await useDeterministicAnalyze(page);
  await seedProject(page, baseProject({
    tasks: [
      task("task_NOCAP001", "마감 전 8h 작업", {
        importance: "critical",
        estimatedHours: 8,
        dueDate: "2026-05-07",
      }),
    ],
    events: [
      {
        id: "evt_BUSY0001",
        taskId: "task_NOCAP001",
        title: "이미 점유된 일정",
        date: "2026-05-07",
        assigneeId: "mem_SMOKE1",
        startTime: "13:00",
        endTime: "17:00",
        approved: true,
        source: "external_blocking",
      },
    ],
  }));

  await runAnalyze(page);
  await page.getByRole("button", { name: "일정안" }).click();
  await expect(page.getByText("미배치 Task 1건")).toBeVisible();
  await expect(page.getByText("no_capacity_before_deadline")).toBeVisible();
});

test("scenario 3 overload and unassigned task exposes workload checks and risk simulation", async ({ page }) => {
  await useDeterministicAnalyze(page);
  await seedProject(page, baseProject({
    members: [
      { id: "mem_SMOKE1", name: "백엔드", role: "Backend", availableHours: 8, workStart: "09:00", workEnd: "18:00" },
      { id: "mem_SMOKE2", name: "프론트", role: "Frontend", availableHours: 40, workStart: "09:00", workEnd: "18:00" },
    ],
    tasks: [
      task("task_LOAD0000", "미할당 중요 작업", { assigneeId: null, importance: "critical" }),
      ...Array.from({ length: 5 }, (_, index) =>
        task(`task_LOAD000${index + 1}`, `과부하 작업 ${index + 1}`, {
          assigneeId: "mem_SMOKE1",
          estimatedHours: 4,
        }),
      ),
    ],
  }));

  await runAnalyze(page);
  await page.getByRole("button", { name: "리스크" }).click();
  await expect(page.getByText("담당자 업무 쏠림")).toBeVisible();
  await expect(page.getByText("fail").first()).toBeVisible();
  await page.getByRole("button", { name: "시뮬레이션" }).first().click();
  await expect(page.getByText("우선순위 개선")).toBeVisible({ timeout: 7000 });
});

test("scenario 4 circular dependency surfaces as a risk blocker to the PM", async ({ page }) => {
  await useDeterministicAnalyze(page);
  await seedProject(page, baseProject({
    tasks: [
      task("task_CYCLE001", "순환 A", { predecessorIds: ["task_CYCLE002"], estimatedHours: 1 }),
      task("task_CYCLE002", "순환 B", { predecessorIds: ["task_CYCLE001"], estimatedHours: 1 }),
    ],
  }));

  await page.getByRole("button", { name: /AI 분석 다시 실행/ }).click();
  await page.getByRole("button", { name: "리스크" }).click();
  await expect(page.getByText("선후행 관계 오류").first()).toBeVisible({ timeout: 7000 });
  await expect(page.getByText("fail").first()).toBeVisible();
  await expect(page.getByText(/순환 경로/).first()).toBeVisible();
  await expect(page.getByText(/선행 Task/).first()).toBeVisible();
});

test("scenario 5 stale schedule approval reanalyzes before a fresh G2 approval", async ({ page }) => {
  await useDeterministicAnalyze(page);
  await seedProject(page, baseProject({
    tasks: [task("task_SMOKE001", "API 연결", { importance: "critical", estimatedHours: 2, dueDate: "2026-05-15" })],
  }));

  await runAnalyze(page);
  await page.getByRole("button", { name: "API 연결" }).first().click();
  await page.getByPlaceholder("Task 이름").fill("API 연결 변경 후 재분석");
  const staleRefresh = page.waitForResponse((response) =>
    response.url().startsWith(BE_BASE_URL) && response.url().includes("/analyze"),
  );
  await page.getByRole("button", { name: /저장/ }).click();
  expect((await staleRefresh).ok()).toBeTruthy();
  await page.getByRole("button", { name: "일정안" }).click();
  const approveResponse = page.waitForResponse((response) =>
    response.url().startsWith(BE_BASE_URL) && response.url().includes("/schedule:approve"),
  );
  await page.getByRole("button", { name: /선택한 일정 승인/ }).click();
  expect((await approveResponse).ok()).toBeTruthy();
  await expect(page.getByText("API 연결 변경 후 재분석").last()).toBeVisible({ timeout: 7000 });
});
