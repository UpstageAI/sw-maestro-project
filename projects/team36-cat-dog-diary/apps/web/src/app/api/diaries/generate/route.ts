// POST /api/diaries/generate — ADR-0008 §C generate.
// 펫 메타 fetch → 한도 검증 → signed URL 발급 → recent_diaries fetch →
// Gateway SSE stream → mediator가 result 이벤트에서 INSERT/quota → meta 이벤트.

import { type NextRequest } from "next/server";
import type {
  GatewayGenerateRequest,
  StreamEvent,
} from "@cat-dog-diary/shared-types";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { errorResponse } from "@/lib/api/error";
import { GatewayError, gatewayStream } from "@/lib/server/gateway";
import { mediateStream, sseResponse } from "@/lib/server/diary-stream";
import { generateSchema } from "@/lib/validators/diary";

const PHOTO_BUCKET = "pet-photos";
const SIGNED_URL_TTL = 3600;
const DAILY_NEW_LIMIT = 5;
const RECENT_DIARIES_LIMIT = 3;
const MAX_PHOTO_SIZE = 10 * 1024 * 1024;
const ALLOWED_MIME = new Set(["image/jpeg", "image/png"]);

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
  const parsed = generateSchema.safeParse(raw);
  if (!parsed.success) {
    return errorResponse(
      "VALIDATION_FAILED",
      parsed.error.issues.map((i) => i.message).join("; "),
    );
  }
  const { pet_id, photo_path, keywords } = parsed.data;

  // 1. 펫 메타 fetch (RLS가 alive + owner 강제 → 없으면 PET_DELETED 또는 NOT_FOUND).
  const { data: pet, error: petErr } = await supabase
    .from("pets")
    .select("id, honorific, species, gender, deleted_at")
    .eq("id", pet_id)
    .maybeSingle();
  if (petErr) return errorResponse("INTERNAL_ERROR", petErr.message);
  if (!pet) return errorResponse("NOT_FOUND", "해당 펫을 찾을 수 없습니다");
  if (pet.deleted_at) {
    return errorResponse(
      "PET_DELETED",
      "삭제된 펫에는 일기를 만들 수 없습니다",
    );
  }

  // 2. 한도 검증 (Asia/Seoul 기준).
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const { data: quota, error: quotaErr } = await supabase
    .from("usage_quotas")
    .select("generations_count")
    .eq("quota_date", today)
    .maybeSingle();
  if (quotaErr) return errorResponse("INTERNAL_ERROR", quotaErr.message);
  const currentCount = quota?.generations_count ?? 0;
  if (currentCount >= DAILY_NEW_LIMIT) {
    return errorResponse(
      "DAILY_QUOTA_EXCEEDED",
      "오늘 새 일기 한도(5회)를 모두 썼어요",
    );
  }

  // 3. Storage object metadata 검증 (ADR-0009 BFF 2차).
  const { data: info, error: infoErr } = await supabase.storage
    .from(PHOTO_BUCKET)
    .info(photo_path);
  if (infoErr || !info) {
    return errorResponse("VALIDATION_FAILED", "사진을 찾을 수 없습니다");
  }
  const size = (info.size ?? info.metadata?.size) as number | undefined;
  if (typeof size === "number" && size > MAX_PHOTO_SIZE) {
    return errorResponse("VALIDATION_FAILED", "사진은 10MB 이하여야 합니다");
  }
  const mime = (info.contentType ?? info.metadata?.mimetype ?? "") as string;
  if (mime && !ALLOWED_MIME.has(mime)) {
    return errorResponse("VALIDATION_FAILED", "JPG 또는 PNG만 지원합니다");
  }

  // 4. signed URL 발급.
  const { data: signed, error: signErr } = await supabase.storage
    .from(PHOTO_BUCKET)
    .createSignedUrl(photo_path, SIGNED_URL_TTL);
  if (signErr || !signed?.signedUrl) {
    return errorResponse(
      "INTERNAL_ERROR",
      signErr?.message ?? "signed URL 발급 실패",
    );
  }

  // 5. 직전 diary_text 3개.
  const { data: recent, error: recentErr } = await supabase
    .from("diaries")
    .select("diary_text")
    .eq("pet_id", pet_id)
    .order("created_at", { ascending: false })
    .limit(RECENT_DIARIES_LIMIT);
  if (recentErr) return errorResponse("INTERNAL_ERROR", recentErr.message);
  const recentDiaries = (recent ?? []).map((r) => r.diary_text as string);

  // 6. Gateway SSE stream 시작.
  const sessionId = crypto.randomUUID();
  const gatewayBody: GatewayGenerateRequest = {
    session_id: sessionId,
    seq: 1,
    pet_id,
    photo_signed_url: signed.signedUrl,
    keywords,
    honorific: pet.honorific,
    species: pet.species,
    gender: pet.gender,
    recent_diaries: recentDiaries,
  };
  let gatewayRes: Response;
  try {
    gatewayRes = await gatewayStream("/diary/generate", gatewayBody, accessToken);
  } catch (e) {
    if (e instanceof GatewayError) {
      return errorResponse("GATEWAY_ERROR", e.message);
    }
    return errorResponse(
      "INTERNAL_ERROR",
      e instanceof Error ? e.message : "Gateway 호출 실패",
    );
  }

  // 7. result 이벤트에서 INSERT + quota 차감 → meta emit.
  // vision_description은 vision_done 이벤트로 mediator가 가로챈 값.
  const stream = mediateStream(gatewayRes.body!, async (result, vision): Promise<StreamEvent> => {
    const { data: gen, error: genErr } = await supabase
      .from("diary_generations")
      .insert({
        owner_id: user.id,
        pet_id,
        session_id: sessionId,
        seq: 1,
        photo_path,
        keywords,
        honorific_used: pet.honorific,
        species_used: pet.species,
        gender_used: pet.gender,
        regen_feedback: null,
        diary_text: result.diary_text,
        short_caption: result.short_caption,
        mood_tag: result.mood_tag,
        vision_description: vision,
      })
      .select("id")
      .single();
    if (genErr) return { type: "error", message: genErr.message };

    // usage_quotas 차감 (best-effort, 실패해도 meta는 정상 — ADR-0008).
    if (quota) {
      await supabase
        .from("usage_quotas")
        .update({ generations_count: currentCount + 1 })
        .eq("quota_date", today);
    } else {
      await supabase.from("usage_quotas").insert({
        owner_id: user.id,
        quota_date: today,
        generations_count: 1,
      });
    }

    return {
      type: "meta",
      generation_id: gen.id,
      session_id: sessionId,
      regenerate_remaining: 3,
      today_new_remaining: Math.max(0, DAILY_NEW_LIMIT - (currentCount + 1)),
    };
  });

  return sseResponse(stream);
}
