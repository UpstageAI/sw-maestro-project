// 오늘 신규 일기 생성 잔여 횟수. RSC + GET /api/usage/today 공유.

import type { SupabaseClient } from "@supabase/supabase-js";

const DAILY_NEW_LIMIT = 5;

export async function getUsageToday(
  supabase: SupabaseClient,
): Promise<{ new_remaining: number }> {
  // usage_quotas.quota_date는 Asia/Seoul 기준. row가 없으면 오늘 사용량 0으로 간주.
  // RLS가 owner_id = auth.uid() 강제하므로 추가 필터 불필요.
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());

  const { data, error } = await supabase
    .from("usage_quotas")
    .select("generations_count")
    .eq("quota_date", today)
    .maybeSingle();

  if (error) throw error;
  const used = data?.generations_count ?? 0;
  return { new_remaining: Math.max(0, DAILY_NEW_LIMIT - used) };
}
