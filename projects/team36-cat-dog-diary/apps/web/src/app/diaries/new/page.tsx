// /diaries/new — pet_id 가드 + usage today 가드 → NewDiaryClient.
// pet_id 누락 / 다른 사용자 / deleted_at / 한도 0 → / redirect (ADR-0013 §일기 추가 진입).

import { redirect } from "next/navigation";
import type { Pet } from "@cat-dog-diary/shared-types";
import { SiteHeader } from "@/components/site-header";
import { getCurrentUser } from "@/lib/server/auth";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { getUsageToday } from "@/lib/server/usage";
import { NewDiaryClient } from "./new-diary-client";

type Props = { searchParams: Promise<{ pet_id?: string }> };

const HERO_DATE_FMT = new Intl.DateTimeFormat("en-US", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

export default async function NewDiaryPage({ searchParams }: Props) {
  const { pet_id } = await searchParams;
  if (!pet_id) redirect("/");

  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const supabase = await createSupabaseServerClient();

  // RLS가 본인 alive 펫만 노출 → 없으면 redirect.
  const { data: pet } = await supabase
    .from("pets")
    .select("id, name, species, honorific, gender, created_at, updated_at")
    .eq("id", pet_id)
    .maybeSingle();
  if (!pet) redirect("/");

  // 한도 도달 시 페이지 진입 차단 (ADR-0013 §한도 도달 처리).
  const usage = await getUsageToday(supabase);
  if (usage.new_remaining <= 0) redirect("/");

  const heroDate = HERO_DATE_FMT.format(new Date()).replace(/\//g, ".");

  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />

      {/* Hero 헤더 — deep 색블록 + 큰 display typography */}
      <section className="bg-deep text-background px-6 py-20 sm:px-10 lg:py-24">
        <div className="mx-auto max-w-[1600px]">
          <div className="mb-8 flex items-center gap-3 text-sm tracking-[0.3em] text-accent uppercase">
            <span className="h-px w-8 bg-accent" />
            <span>New Diary · {heroDate}</span>
          </div>
          <h1
            className="font-display text-5xl leading-[0.95] sm:text-6xl lg:text-7xl"
            style={{ letterSpacing: "-0.02em" }}
          >
            {pet.name}의<br />
            <span className="text-accent">오늘</span>을 기록할 시간
          </h1>
          <p className="mt-8 text-lg leading-relaxed text-background/70 sm:mt-10 sm:text-xl">
            사진 한 장과 키워드 한 줄.<br />
            1인칭 시점의 따뜻한 일기가 자동으로 완성돼요.
          </p>
        </div>
      </section>

      {/* 본문 — cream 폼/결과 영역 */}
      <section className="bg-background text-foreground px-6 py-16 sm:px-10 lg:py-20 flex-1">
        <div className="mx-auto w-full max-w-xl">
          <NewDiaryClient pet={pet as Pet} initialNewRemaining={usage.new_remaining} />
        </div>
      </section>
    </main>
  );
}
