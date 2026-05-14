// 펫 사진 업로드 — ADR-0009 정합. 클라이언트 직접 PUT to Storage, RLS는
// path 첫 segment = owner_id 강제. long edge 1024px Canvas 리사이즈.

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export const PHOTO_BUCKET = "pet-photos";
export const MAX_PHOTO_SIZE = 10 * 1024 * 1024;
export const ALLOWED_MIME = ["image/jpeg", "image/png"] as const;
const LONG_EDGE = 1024;
const JPEG_QUALITY = 0.9;

export class PhotoUploadError extends Error {}

function extFromMime(mime: string): "jpg" | "png" {
  if (mime === "image/png") return "png";
  return "jpg";
}

async function resizeToBlob(file: File): Promise<Blob> {
  const bitmap = await createImageBitmap(file);
  const { width, height } = bitmap;
  const longEdge = Math.max(width, height);
  const scale = longEdge > LONG_EDGE ? LONG_EDGE / longEdge : 1;
  const targetW = Math.round(width * scale);
  const targetH = Math.round(height * scale);

  const canvas = document.createElement("canvas");
  canvas.width = targetW;
  canvas.height = targetH;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new PhotoUploadError("Canvas 컨텍스트를 만들 수 없어요");
  ctx.drawImage(bitmap, 0, 0, targetW, targetH);
  bitmap.close();

  const targetType = file.type === "image/png" ? "image/png" : "image/jpeg";
  const blob: Blob | null = await new Promise((resolve) =>
    canvas.toBlob(resolve, targetType, JPEG_QUALITY),
  );
  if (!blob) throw new PhotoUploadError("이미지 변환에 실패했어요");
  return blob;
}

function buildPath(ownerId: string, mime: string): string {
  const now = new Date();
  const yyyy = String(now.getFullYear());
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  return `${ownerId}/diaries/${yyyy}/${mm}/${crypto.randomUUID()}.${extFromMime(mime)}`;
}

export async function uploadPetPhoto(file: File): Promise<string> {
  if (!ALLOWED_MIME.includes(file.type as (typeof ALLOWED_MIME)[number])) {
    throw new PhotoUploadError("JPG 또는 PNG만 지원해요");
  }
  if (file.size > MAX_PHOTO_SIZE) {
    throw new PhotoUploadError("사진은 10MB 이하여야 해요");
  }

  const supabase = createSupabaseBrowserClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new PhotoUploadError("로그인이 필요해요");

  const blob = await resizeToBlob(file);
  const path = buildPath(user.id, file.type);

  const { error } = await supabase.storage
    .from(PHOTO_BUCKET)
    .upload(path, blob, {
      contentType: blob.type,
      cacheControl: "3600",
      upsert: false,
    });
  if (error) throw new PhotoUploadError(error.message);

  return path;
}
