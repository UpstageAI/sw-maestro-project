// 펫별 일기 피드 조회 (cursor pagination + signed URL 발급).
// RSC + GET /api/diaries 공유. cookie 기반 supabase server client 가정.

import type { SupabaseClient } from "@supabase/supabase-js";
import type { Diary } from "@cat-dog-diary/shared-types";

const PHOTO_BUCKET = "pet-photos";
const PHOTO_SIGNED_URL_TTL = 3600; // 1h, ADR-0009
const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 50;

interface CursorPayload {
  c: string; // created_at ISO
  i: string; // diary id
}

function encodeCursor(c: CursorPayload): string {
  return Buffer.from(JSON.stringify(c), "utf-8").toString("base64url");
}

function decodeCursor(raw: string): CursorPayload | null {
  try {
    const json = Buffer.from(raw, "base64url").toString("utf-8");
    const parsed = JSON.parse(json) as Partial<CursorPayload>;
    if (typeof parsed.c !== "string" || typeof parsed.i !== "string") return null;
    return parsed as CursorPayload;
  } catch {
    return null;
  }
}

export interface ListDiariesOptions {
  petId: string;
  cursor?: string;
  limit?: number;
}

export async function listDiariesForPet(
  supabase: SupabaseClient,
  opts: ListDiariesOptions,
): Promise<{ items: Diary[]; next_cursor: string | null }> {
  const limit = Math.min(Math.max(opts.limit ?? DEFAULT_LIMIT, 1), MAX_LIMIT);

  let q = supabase
    .from("diaries")
    .select(
      "id, pet_id, diary_text, short_caption, mood_tag, created_at, source_generation_id",
    )
    .eq("pet_id", opts.petId)
    .order("created_at", { ascending: false })
    .order("id", { ascending: false })
    .limit(limit + 1);

  if (opts.cursor) {
    const c = decodeCursor(opts.cursor);
    if (c) {
      // (created_at, id) < (c.c, c.i) — DESC 정렬에서 다음 페이지.
      q = q.or(
        `created_at.lt.${c.c},and(created_at.eq.${c.c},id.lt.${c.i})`,
      );
    }
  }

  const { data: rows, error } = await q;
  if (error) throw error;

  const hasMore = (rows?.length ?? 0) > limit;
  const page = hasMore ? rows!.slice(0, limit) : (rows ?? []);

  if (page.length === 0) return { items: [], next_cursor: null };

  // photo_path는 diary_generations에 있음 → source_generation_id로 join lookup.
  const genIds = page.map((r) => r.source_generation_id);
  const { data: gens, error: genErr } = await supabase
    .from("diary_generations")
    .select("id, photo_path")
    .in("id", genIds);
  if (genErr) throw genErr;

  const pathById = new Map<string, string>(
    (gens ?? []).map((g) => [g.id as string, g.photo_path as string]),
  );

  const paths = page
    .map((r) => pathById.get(r.source_generation_id))
    .filter((p): p is string => typeof p === "string");

  const { data: signed, error: signErr } = await supabase.storage
    .from(PHOTO_BUCKET)
    .createSignedUrls(paths, PHOTO_SIGNED_URL_TTL);
  if (signErr) throw signErr;

  const urlByPath = new Map<string, string>();
  for (const s of signed ?? []) {
    if (s.path && s.signedUrl) urlByPath.set(s.path, s.signedUrl);
  }

  const items: Diary[] = page.map((r) => {
    const path = pathById.get(r.source_generation_id) ?? "";
    return {
      id: r.id,
      pet_id: r.pet_id,
      diary_text: r.diary_text,
      short_caption: r.short_caption,
      mood_tag: r.mood_tag,
      photo_signed_url: urlByPath.get(path) ?? "",
      created_at: r.created_at,
    };
  });

  const next_cursor = hasMore
    ? encodeCursor({
        c: page[page.length - 1].created_at,
        i: page[page.length - 1].id,
      })
    : null;

  return { items, next_cursor };
}
