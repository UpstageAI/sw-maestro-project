import { NextResponse } from "next/server";
import type { UsageTodayResponse } from "@cat-dog-diary/shared-types";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { errorResponse } from "@/lib/api/error";
import { getUsageToday } from "@/lib/server/usage";

export async function GET() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return errorResponse("UNAUTHENTICATED", "로그인이 필요합니다");

  try {
    const body: UsageTodayResponse = await getUsageToday(supabase);
    return NextResponse.json(body);
  } catch (e) {
    return errorResponse(
      "INTERNAL_ERROR",
      e instanceof Error ? e.message : "usage 조회 실패",
    );
  }
}
