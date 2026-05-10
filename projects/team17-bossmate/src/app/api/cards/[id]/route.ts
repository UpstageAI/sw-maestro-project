import { NextResponse } from "next/server";
import { getJob } from "@/lib/store";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const job = await getJob(id);

  if (!job) {
    return NextResponse.json(
      { error: "생성 작업을 찾을 수 없습니다. 다시 시도해주세요." },
      { status: 404 },
    );
  }

  return NextResponse.json(job);
}
