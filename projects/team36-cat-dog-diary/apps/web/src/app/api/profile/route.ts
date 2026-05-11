import { NextResponse, type NextRequest } from "next/server";
import type {
  Profile,
  UpdateProfileResponse,
} from "@cat-dog-diary/shared-types";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { updateProfileSchema } from "@/lib/validators/profile";
import { errorResponse } from "@/lib/api/error";

export async function PATCH(request: NextRequest) {
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

  const parsed = updateProfileSchema.safeParse(raw);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_FAILED",
      parsed.error.issues.map((i) => i.message).join("; "),
    );
  }

  // RLS profiles_update_own이 id = auth.uid() 강제 → eq("id", user.id) 안 걸어도
  // 무관하지만 명시해두면 미래에 service_role로 갈아탈 때 안전.
  const { data, error } = await supabase
    .from("profiles")
    .update(parsed.data)
    .eq("id", user.id)
    .select("display_name, updated_at")
    .single();

  if (error) {
    if (error.code === "PGRST116") {
      return errorResponse("NOT_FOUND", "프로필을 찾을 수 없습니다");
    }
    return errorResponse("INTERNAL_ERROR", error.message);
  }

  const body: UpdateProfileResponse = data as Profile;
  return NextResponse.json(body);
}
