// GET /api/diaries/:id/sns-image — 9:16 (1080×1920) PNG 서버 렌더.
// 클라이언트 캡처(html-to-image)는 SVG-to-image 단계에서 inline @font-face가
// 적용 안 되어 디바이스 시스템 폰트로 fallback되는 한계가 있어, OS별로 글리프
// metrics가 달라 텍스트 시각 크기가 다르게 나오는 문제를 해결.
// Satori(@vercel/og)가 woff2/otf의 글리프 path로 직접 그려 환경 무관 동일 PNG.

import { ImageResponse } from "next/og";
import type { MoodTag } from "@cat-dog-diary/shared-types";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { errorResponse } from "@/lib/api/error";

export const runtime = "edge";

const PHOTO_BUCKET = "pet-photos";
const SIGNED_URL_TTL = 60;

const MOOD_COLOR: Record<MoodTag, string> = {
  행복: "#f5c870",
  신남: "#ff9f6e",
  평온: "#9bb196",
  졸림: "#b5a8c7",
  심심: "#b5a89a",
  슬픔: "#8c9eb5",
  까칠: "#c47054",
};

const DATE_FMT = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "long",
  day: "numeric",
});

// 본문 200~400자 모두 텍스트 영역에 fit하도록 글자수 구간별 폰트.
function diaryTextStyle(len: number) {
  if (len <= 220) return { fontSize: 30, lineHeight: 1.7 };
  if (len <= 320) return { fontSize: 26, lineHeight: 1.6 };
  return { fontSize: 22, lineHeight: 1.55 };
}

// 모듈-level 캐시 — 첫 호출만 fetch. Vercel/Node 핫 인스턴스에서 유지.
let fontsCache: {
  regular: ArrayBuffer;
  bold: ArrayBuffer;
  cafe: ArrayBuffer;
} | null = null;

async function loadFonts(origin: string) {
  if (fontsCache) return fontsCache;
  const [regular, bold, cafe] = await Promise.all([
    fetch(`${origin}/fonts/Pretendard-Regular.otf`).then((r) => r.arrayBuffer()),
    fetch(`${origin}/fonts/Pretendard-Bold.otf`).then((r) => r.arrayBuffer()),
    fetch(`${origin}/fonts/Cafe24Ssurround.woff`).then((r) => r.arrayBuffer()),
  ]);
  fontsCache = { regular, bold, cafe };
  return fontsCache;
}

type Ctx = { params: Promise<{ id: string }> };

export async function GET(request: Request, ctx: Ctx) {
  try {
    return await handle(request, ctx);
  } catch (err) {
    console.error("[SNS image] error:", err);
    return errorResponse(
      "INTERNAL_ERROR",
      err instanceof Error ? err.message : "이미지 생성 실패",
    );
  }
}

async function handle(request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  const origin = new URL(request.url).origin;

  // 폰트 fetch는 DB 쿼리/photo fetch와 병렬 — auth 무관.
  const fontsPromise = loadFonts(origin);

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return errorResponse("UNAUTHENTICATED", "로그인이 필요합니다");

  // 일기 fetch. RLS가 owner-only 강제.
  const { data: diary, error: diaryErr } = await supabase
    .from("diaries")
    .select(
      "id, pet_id, diary_text, short_caption, mood_tag, created_at, source_generation_id",
    )
    .eq("id", id)
    .maybeSingle();
  if (diaryErr) return errorResponse("INTERNAL_ERROR", diaryErr.message);
  if (!diary) return errorResponse("NOT_FOUND", "일기를 찾을 수 없어요");

  // 펫 이름 + photo_path 병렬 fetch.
  const [petResult, genResult] = await Promise.all([
    supabase.from("pets").select("name").eq("id", diary.pet_id).maybeSingle(),
    supabase
      .from("diary_generations")
      .select("photo_path")
      .eq("id", diary.source_generation_id)
      .maybeSingle(),
  ]);
  const petName = petResult.data?.name ?? "";
  if (genResult.error) {
    return errorResponse("INTERNAL_ERROR", genResult.error.message);
  }
  if (!genResult.data?.photo_path) {
    return errorResponse("NOT_FOUND", "사진을 찾을 수 없어요");
  }

  // 사진 fetch → base64 inline. Satori는 외부 URL fetch 가능하지만 base64가 더 안정적.
  const { data: signed } = await supabase.storage
    .from(PHOTO_BUCKET)
    .createSignedUrl(genResult.data.photo_path, SIGNED_URL_TTL);
  if (!signed?.signedUrl) {
    return errorResponse("INTERNAL_ERROR", "사진 URL 발급 실패");
  }
  const photoRes = await fetch(signed.signedUrl);
  if (!photoRes.ok) {
    return errorResponse("INTERNAL_ERROR", "사진 다운로드 실패");
  }
  const photoArrayBuffer = await photoRes.arrayBuffer();
  const photoContentType = photoRes.headers.get("content-type") ?? "image/jpeg";
  const photoDataUrl = `data:${photoContentType};base64,${Buffer.from(
    photoArrayBuffer,
  ).toString("base64")}`;

  // 폰트는 위에서 시작한 fetch가 완료되었거나 DB 쿼리·photo fetch와 병렬 진행됨.
  const fonts = await fontsPromise;

  const dateLabel = DATE_FMT.format(new Date(diary.created_at));
  const moodTag = diary.mood_tag as MoodTag;
  const moodColor = MOOD_COLOR[moodTag] ?? "#946652";
  const diaryText = diary.diary_text as string;
  const caption = diary.short_caption as string;
  const ds = diaryTextStyle(diaryText.length);

  return new ImageResponse(
    (
      <div
        style={{
          width: 1080,
          height: 1920,
          display: "flex",
          flexDirection: "column",
          backgroundColor: "#fffaf3",
          color: "#2d2018",
          fontFamily: "Pretendard",
        }}
      >
        {/* 사진 영역: 1080 × 1152 (60%) */}
        <div
          style={{
            width: 1080,
            height: 1152,
            position: "relative",
            display: "flex",
            backgroundColor: "#ebe1cd",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photoDataUrl}
            alt=""
            width={1080}
            height={1152}
            style={{ width: 1080, height: 1152, objectFit: "cover" }}
          />
          {/* 펫 이름 칩 — 좌상단 */}
          <div
            style={{
              position: "absolute",
              top: 36,
              left: 36,
              display: "flex",
              alignItems: "center",
              gap: 10,
              backgroundColor: "rgba(255, 250, 243, 0.92)",
              color: "#2d2018",
              padding: "14px 26px",
              borderRadius: 999,
              fontSize: 30,
              fontWeight: 700,
              boxShadow: "0 6px 20px rgba(0,0,0,0.15)",
            }}
          >
            <span style={{ fontSize: 28, lineHeight: 1 }}>🐾</span>
            <span>{petName}</span>
          </div>
        </div>

        {/* 텍스트 영역: 1080 × 768 (40%) */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            padding: "64px 72px 56px",
            backgroundColor: "#fffaf3",
          }}
        >
          {/* meta-row */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 28,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                backgroundColor: "#ebe1cd",
                borderRadius: 999,
                padding: "12px 24px",
                fontSize: 26,
                fontWeight: 500,
              }}
            >
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: 999,
                  backgroundColor: moodColor,
                }}
              />
              <span>{moodTag}</span>
            </div>
            <div
              style={{
                fontSize: 24,
                color: "#8d7866",
                fontWeight: 500,
              }}
            >
              {dateLabel}
            </div>
          </div>

          {/* caption */}
          <div
            style={{
              display: "flex",
              fontFamily: "Cafe24Ssurround",
              fontSize: 56,
              lineHeight: 1.25,
              color: "#2d2018",
              marginBottom: 32,
            }}
          >
            {caption}
          </div>

          {/* diary body */}
          <div
            style={{
              display: "flex",
              flex: 1,
              fontSize: ds.fontSize,
              lineHeight: ds.lineHeight,
              color: "#2d2018",
              whiteSpace: "pre-wrap",
            }}
          >
            {diaryText}
          </div>

          {/* watermark */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: 24,
              fontSize: 24,
              color: "#946652",
              fontWeight: 700,
            }}
          >
            🐾 냥멍일기
          </div>
        </div>
      </div>
    ),
    {
      width: 1080,
      height: 1920,
      fonts: [
        { name: "Pretendard", data: fonts.regular, weight: 400 },
        { name: "Pretendard", data: fonts.bold, weight: 700 },
        { name: "Cafe24Ssurround", data: fonts.cafe, weight: 700 },
      ],
      // 일기는 immutable이라 1시간 private cache. 같은 일기 재호출은 0초.
      headers: {
        "Cache-Control": "private, max-age=3600, immutable",
      },
    },
  );
}
