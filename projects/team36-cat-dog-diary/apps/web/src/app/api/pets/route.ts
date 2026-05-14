import { NextResponse, type NextRequest } from "next/server";
import type {
  CreatePetResponse,
  ListPetsResponse,
  Pet,
} from "@cat-dog-diary/shared-types";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { createPetSchema } from "@/lib/validators/pet";
import { errorResponse } from "@/lib/api/error";

const PUBLIC_PET_FIELDS =
  "id, name, species, honorific, gender, created_at, updated_at";

export async function GET() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return errorResponse("UNAUTHENTICATED", "로그인이 필요합니다");

  // RLS의 pets_select_own_active가 deleted_at IS NULL을 강제 → 클라이언트는 alive만 받음.
  const { data, error } = await supabase
    .from("pets")
    .select(PUBLIC_PET_FIELDS)
    .order("created_at", { ascending: true });

  if (error) return errorResponse("INTERNAL_ERROR", error.message);

  const body: ListPetsResponse = { items: (data ?? []) as Pet[] };
  return NextResponse.json(body);
}

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

  const parsed = createPetSchema.safeParse(raw);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_FAILED",
      parsed.error.issues.map((i) => i.message).join("; "),
    );
  }

  const { data, error } = await supabase
    .from("pets")
    .insert({ owner_id: user.id, ...parsed.data })
    .select(PUBLIC_PET_FIELDS)
    .single();

  if (error) return errorResponse("INTERNAL_ERROR", error.message);

  const body: CreatePetResponse = data as Pet;
  return NextResponse.json(body, { status: 201 });
}
