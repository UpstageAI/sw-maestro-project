import { NextResponse, after } from "next/server";
import { runPromotionJob } from "@/lib/generator";
import { getJob, setJob } from "@/lib/store";
import type { JobRecord, PromotionRequest } from "@/lib/types";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const existing = await getJob(id);
  if (!existing) {
    return NextResponse.json(
      { error: "재생성할 작업을 찾을 수 없습니다." },
      { status: 404 },
    );
  }

  let feedback = "";
  try {
    const body = (await request.json()) as { feedback?: string };
    feedback = body.feedback?.trim() ?? "";
  } catch {
    feedback = "";
  }

  const newId = crypto.randomUUID();
  const now = new Date().toISOString();
  const newRequest: PromotionRequest = {
    ...existing.request,
    feedback: feedback || existing.request.feedback,
  };
  const job: JobRecord = {
    id: newId,
    status: "pending",
    request: newRequest,
    agentTrace: [],
    startedAt: now,
    updatedAt: now,
  };
  await setJob(job);

  after(async () => {
    await runPromotionJob(newId, newRequest);
  });

  return NextResponse.json({ id: newId, status: job.status }, { status: 202 });
}
