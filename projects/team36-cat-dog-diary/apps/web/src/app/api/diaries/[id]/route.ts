// DELETE /api/diaries/:id — ADR-0008 §C. 일기 hard delete + same-session
// generations 동반 + storage object 삭제 (BFF 트랜잭션 best-effort).

import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { errorResponse } from "@/lib/api/error";

const PHOTO_BUCKET = "pet-photos";

type Ctx = { params: Promise<{ id: string }> };

export async function DELETE(_: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return errorResponse("UNAUTHENTICATED", "로그인이 필요합니다");

  // 1. diary lookup → source_generation_id.
  const { data: diary, error: diaryErr } = await supabase
    .from("diaries")
    .select("id, source_generation_id")
    .eq("id", id)
    .maybeSingle();
  if (diaryErr) return errorResponse("INTERNAL_ERROR", diaryErr.message);
  if (!diary) return errorResponse("NOT_FOUND", "해당 일기를 찾을 수 없습니다");

  // 2. source generation의 session_id 조회.
  const { data: srcGen, error: srcErr } = await supabase
    .from("diary_generations")
    .select("session_id")
    .eq("id", diary.source_generation_id)
    .maybeSingle();
  if (srcErr) return errorResponse("INTERNAL_ERROR", srcErr.message);
  // srcGen이 null이면 데이터 정합 깨진 케이스 — 그래도 diary는 삭제 가능.
  const sessionId = srcGen?.session_id as string | undefined;

  // 3. session_id가 있으면 same-session generations photo_path 모으기.
  let photoPaths: string[] = [];
  if (sessionId) {
    const { data: gens, error: gensErr } = await supabase
      .from("diary_generations")
      .select("photo_path")
      .eq("session_id", sessionId);
    if (gensErr) return errorResponse("INTERNAL_ERROR", gensErr.message);
    photoPaths = Array.from(
      new Set(
        (gens ?? [])
          .map((g) => g.photo_path as string)
          .filter((p) => typeof p === "string" && p.length > 0),
      ),
    );
  }

  // 4. diaries 먼저 삭제 (FK source_generation_id 제약 회피).
  const { error: delDiaryErr } = await supabase
    .from("diaries")
    .delete()
    .eq("id", id);
  if (delDiaryErr) return errorResponse("INTERNAL_ERROR", delDiaryErr.message);

  // 5. 동세션 generations 삭제. RLS가 owner-only 강제.
  if (sessionId) {
    const { error: delGenErr } = await supabase
      .from("diary_generations")
      .delete()
      .eq("session_id", sessionId);
    if (delGenErr) {
      // generation 삭제 실패해도 diary는 이미 삭제됨 → 응답은 success.
      console.error("delete generations failed:", delGenErr.message);
    }
  }

  // 6. storage object 동반 삭제 (best-effort).
  if (photoPaths.length > 0) {
    const { error: storageErr } = await supabase.storage
      .from(PHOTO_BUCKET)
      .remove(photoPaths);
    if (storageErr) {
      console.error("delete storage objects failed:", storageErr.message);
    }
  }

  return new NextResponse(null, { status: 204 });
}
