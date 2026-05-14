import { NextResponse, type NextRequest } from "next/server";
import type {
  AdoptDiaryResponse,
  ListDiariesResponse,
} from "@cat-dog-diary/shared-types";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { errorResponse } from "@/lib/api/error";
import { listDiariesForPet } from "@/lib/server/diaries";
import { adoptSchema } from "@/lib/validators/diary";

export async function GET(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return errorResponse("UNAUTHENTICATED", "로그인이 필요합니다");

  const { searchParams } = new URL(request.url);
  const petId = searchParams.get("petId");
  if (!petId) {
    return errorResponse("VALIDATION_FAILED", "petId 쿼리 파라미터가 필요합니다");
  }

  const cursor = searchParams.get("cursor") ?? undefined;
  const limitRaw = searchParams.get("limit");
  const limit = limitRaw ? Number(limitRaw) : undefined;
  if (limit !== undefined && (!Number.isFinite(limit) || limit < 1)) {
    return errorResponse("VALIDATION_FAILED", "limit은 양의 정수여야 합니다");
  }

  try {
    const body: ListDiariesResponse = await listDiariesForPet(supabase, {
      petId,
      cursor,
      limit,
    });
    return NextResponse.json(body);
  } catch (e) {
    return errorResponse(
      "INTERNAL_ERROR",
      e instanceof Error ? e.message : "일기 조회 실패",
    );
  }
}

// POST /api/diaries — generation 채택 (ADR-0008 §C). diaries INSERT.
export async function POST(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return errorResponse("UNAUTHENTICATED", "로그인이 필요합니다");

  let raw: unknown;
  try {
    raw = await request.json();
  } catch {
    return errorResponse("VALIDATION_FAILED", "JSON 파싱 실패");
  }
  const parsed = adoptSchema.safeParse(raw);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_FAILED",
      parsed.error.issues.map((i) => i.message).join("; "),
    );
  }

  // RLS가 owner의 generation만 보임 → 다른 사용자 id면 maybeSingle null.
  const { data: gen, error: genErr } = await supabase
    .from("diary_generations")
    .select("id, pet_id, diary_text, short_caption, mood_tag")
    .eq("id", parsed.data.source_generation_id)
    .maybeSingle();
  if (genErr) return errorResponse("INTERNAL_ERROR", genErr.message);
  if (!gen) {
    return errorResponse("NOT_FOUND", "해당 생성 결과를 찾을 수 없습니다");
  }

  const { data: diary, error: insErr } = await supabase
    .from("diaries")
    .insert({
      owner_id: user.id,
      pet_id: gen.pet_id,
      source_generation_id: gen.id,
      diary_text: gen.diary_text,
      short_caption: gen.short_caption,
      mood_tag: gen.mood_tag,
    })
    .select("id")
    .single();
  if (insErr) {
    // diaries.source_generation_id UNIQUE → 같은 generation 두 번 채택 시 23505.
    if (insErr.code === "23505") {
      return errorResponse("VALIDATION_FAILED", "이미 채택된 일기입니다");
    }
    return errorResponse("INTERNAL_ERROR", insErr.message);
  }

  const body: AdoptDiaryResponse = { diary_id: diary.id };
  return NextResponse.json(body, { status: 201 });
}
