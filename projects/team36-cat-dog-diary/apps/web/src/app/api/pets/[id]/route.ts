import { NextResponse, type NextRequest } from "next/server";
import type { Pet, UpdatePetResponse } from "@cat-dog-diary/shared-types";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { updatePetSchema } from "@/lib/validators/pet";
import { errorResponse } from "@/lib/api/error";

const PUBLIC_PET_FIELDS =
  "id, name, species, honorific, gender, created_at, updated_at";

type Ctx = { params: Promise<{ id: string }> };

export async function PATCH(request: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
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

  const parsed = updatePetSchema.safeParse(raw);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_FAILED",
      parsed.error.issues.map((i) => i.message).join("; "),
    );
  }

  const { data, error } = await supabase
    .from("pets")
    .update(parsed.data)
    .eq("id", id)
    .select(PUBLIC_PET_FIELDS)
    .single();

  // RLS가 owner 검증 실패 시 0행 반환 → supabase-js single()이 PGRST116. 404로 변환.
  if (error) {
    if (error.code === "PGRST116") {
      return errorResponse("NOT_FOUND", "해당 펫을 찾을 수 없습니다");
    }
    return errorResponse("INTERNAL_ERROR", error.message);
  }

  const body: UpdatePetResponse = data as Pet;
  return NextResponse.json(body);
}

export async function DELETE(_: NextRequest, ctx: Ctx) {
  const { id } = await ctx.params;
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return errorResponse("UNAUTHENTICATED", "로그인이 필요합니다");

  // soft delete: deleted_at = now() UPDATE를 SECURITY DEFINER RPC로 실행.
  // 직접 UPDATE 하면 SELECT policy의 deleted_at IS NULL referenced column 변경 →
  // PostgreSQL이 NEW row를 SELECT policy로 재검사 → 42501. RPC가 RLS 우회 + 명시적 owner 체크.
  const { error } = await supabase.rpc("soft_delete_pet", { p_id: id });

  if (error) {
    if (error.code === "P0002")
      return errorResponse("NOT_FOUND", "해당 펫을 찾을 수 없습니다");
    if (error.code === "42501")
      return errorResponse("UNAUTHENTICATED", "권한이 없습니다");
    return errorResponse("INTERNAL_ERROR", error.message);
  }

  return new NextResponse(null, { status: 204 });
}
