// POST /api/diaries/regenerate — ADR-0008 §C regenerate.
// session 검증 → seq 결정 → 재생성 한도 ≤3 → 펫 메타 fetch (snapshot 갱신) →
// signed URL → 직전 generation diary_text → Gateway SSE → mediator INSERT → meta.
// usage_quotas 차감 X (재생성은 일일 한도와 무관 — ADR-0008 §카운트 정책).

import { type NextRequest } from "next/server";
import type {
  GatewayRegenerateRequest,
  StreamEvent,
} from "@cat-dog-diary/shared-types";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { errorResponse } from "@/lib/api/error";
import { GatewayError, gatewayStream } from "@/lib/server/gateway";
import { mediateStream, sseResponse } from "@/lib/server/diary-stream";
import { regenerateSchema } from "@/lib/validators/diary";

const PHOTO_BUCKET = "pet-photos";
const SIGNED_URL_TTL = 3600;
const REGEN_LIMIT = 3;
const RECENT_DIARIES_LIMIT = 3;

export async function POST(request: NextRequest) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return errorResponse("UNAUTHENTICATED", "로그인이 필요합니다");

  const {
    data: { session },
  } = await supabase.auth.getSession();
  const accessToken = session?.access_token;
  if (!accessToken) {
    return errorResponse("UNAUTHENTICATED", "세션 토큰이 없습니다");
  }

  let raw: unknown;
  try {
    raw = await request.json();
  } catch {
    return errorResponse("VALIDATION_FAILED", "JSON 파싱 실패");
  }
  const parsed = regenerateSchema.safeParse(raw);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_FAILED",
      parsed.error.issues.map((i) => i.message).join("; "),
    );
  }
  const { session_id, pet_id, photo_path, keywords, feedback } = parsed.data;

  // 1. 펫 메타 + alive 검증.
  const { data: pet, error: petErr } = await supabase
    .from("pets")
    .select("id, honorific, species, gender, deleted_at")
    .eq("id", pet_id)
    .maybeSingle();
  if (petErr) return errorResponse("INTERNAL_ERROR", petErr.message);
  if (!pet) return errorResponse("NOT_FOUND", "해당 펫을 찾을 수 없습니다");
  if (pet.deleted_at) {
    return errorResponse("PET_DELETED", "삭제된 펫에는 일기를 만들 수 없습니다");
  }

  // 2. 같은 session의 최신 generation 조회 → seq 결정 + previous_diary_text +
  //    vision_description echo (있으면 gateway가 vision LLM 호출 skip).
  const { data: lastGen, error: lastErr } = await supabase
    .from("diary_generations")
    .select("seq, diary_text, pet_id, vision_description")
    .eq("session_id", session_id)
    .order("seq", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (lastErr) return errorResponse("INTERNAL_ERROR", lastErr.message);
  if (!lastGen) {
    return errorResponse("NOT_FOUND", "해당 세션을 찾을 수 없습니다");
  }
  if (lastGen.pet_id !== pet_id) {
    return errorResponse("VALIDATION_FAILED", "세션과 펫이 일치하지 않습니다");
  }
  const nextSeq = lastGen.seq + 1;
  if (nextSeq > 1 + REGEN_LIMIT) {
    return errorResponse(
      "REGEN_QUOTA_EXCEEDED",
      "이 세션의 재생성 한도(3회)를 모두 썼어요",
    );
  }

  // 3. signed URL 발급 (사진은 같은 path 재사용 — ADR-0009).
  const { data: signed, error: signErr } = await supabase.storage
    .from(PHOTO_BUCKET)
    .createSignedUrl(photo_path, SIGNED_URL_TTL);
  if (signErr || !signed?.signedUrl) {
    return errorResponse(
      "INTERNAL_ERROR",
      signErr?.message ?? "signed URL 발급 실패",
    );
  }

  // 4. 직전 diary_text 3개 (재생성 컨텍스트, 채택된 일기 기준).
  const { data: recent, error: recentErr } = await supabase
    .from("diaries")
    .select("diary_text")
    .eq("pet_id", pet_id)
    .order("created_at", { ascending: false })
    .limit(RECENT_DIARIES_LIMIT);
  if (recentErr) return errorResponse("INTERNAL_ERROR", recentErr.message);
  const recentDiaries = (recent ?? []).map((r) => r.diary_text as string);

  // 5. Gateway SSE stream 시작.
  // vision_description forward — null 아니면 gateway가 analyze_image skip.
  const forwardedVision = (lastGen.vision_description as string | null) ?? undefined;
  const gatewayBody: GatewayRegenerateRequest = {
    session_id,
    seq: nextSeq,
    pet_id,
    photo_signed_url: signed.signedUrl,
    keywords,
    honorific: pet.honorific,
    species: pet.species,
    gender: pet.gender,
    recent_diaries: recentDiaries,
    previous_diary_text: lastGen.diary_text as string,
    feedback,
    vision_description: forwardedVision,
  };
  let gatewayRes: Response;
  try {
    gatewayRes = await gatewayStream(
      "/diary/regenerate",
      gatewayBody,
      accessToken,
    );
  } catch (e) {
    if (e instanceof GatewayError) {
      return errorResponse("GATEWAY_ERROR", e.message);
    }
    return errorResponse(
      "INTERNAL_ERROR",
      e instanceof Error ? e.message : "Gateway 호출 실패",
    );
  }

  // 6. result 이벤트에서 INSERT (snapshot 갱신 + vision echo) → meta emit.
  // skip된 경우 vision은 null 들어옴 → forward한 값 echo.
  // 새로 호출된 경우(NULL fallback) vision_done 받은 새 값 사용.
  const stream = mediateStream(gatewayRes.body!, async (result, vision): Promise<StreamEvent> => {
    const visionToStore = vision ?? forwardedVision ?? null;
    const { data: gen, error: genErr } = await supabase
      .from("diary_generations")
      .insert({
        owner_id: user.id,
        pet_id,
        session_id,
        seq: nextSeq,
        photo_path,
        keywords,
        honorific_used: pet.honorific,
        species_used: pet.species,
        gender_used: pet.gender,
        regen_feedback: feedback ?? null,
        diary_text: result.diary_text,
        short_caption: result.short_caption,
        mood_tag: result.mood_tag,
        vision_description: visionToStore,
      })
      .select("id")
      .single();
    if (genErr) return { type: "error", message: genErr.message };

    return {
      type: "meta",
      generation_id: gen.id,
      session_id,
      regenerate_remaining: 1 + REGEN_LIMIT - nextSeq,
    };
  });

  return sseResponse(stream);
}
