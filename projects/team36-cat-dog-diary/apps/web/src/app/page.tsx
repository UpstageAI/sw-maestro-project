import Link from "next/link";
import { redirect } from "next/navigation";
import type { Diary, Pet, Profile } from "@cat-dog-diary/shared-types";
import { buttonVariants } from "@/components/ui/button";
import { EmptyStateCard } from "@/components/empty-state-card";
import { PetRow } from "@/components/pet-row";
import { SiteHeader } from "@/components/site-header";
import { getCurrentUser } from "@/lib/server/auth";
import { listDiariesForPet } from "@/lib/server/diaries";
import { getUsageToday } from "@/lib/server/usage";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { cn } from "@/lib/utils";

const PET_FIELDS =
  "id, name, species, honorific, gender, created_at, updated_at";
const ROW_DIARY_LIMIT = 12;

const HERO_DATE_FMT = new Intl.DateTimeFormat("en-US", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

function daysTogether(createdAt: string): number {
  const ms = Date.now() - new Date(createdAt).getTime();
  return Math.max(1, Math.floor(ms / (1000 * 60 * 60 * 24)) + 1);
}

export default async function Home() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const supabase = await createSupabaseServerClient();

  const [{ data: petsData, error: petsError }, { data: profileData }] =
    await Promise.all([
      supabase
        .from("pets")
        .select(PET_FIELDS)
        .order("created_at", { ascending: true }),
      supabase
        .from("profiles")
        .select("display_name, updated_at")
        .eq("id", user.id)
        .maybeSingle(),
    ]);
  if (petsError) throw petsError;

  const pets = (petsData ?? []) as Pet[];
  const profile = (profileData ?? null) as Profile | null;
  const displayName = profile?.display_name ?? user.email ?? "사용자";

  const [usage, ...rows] = await Promise.all([
    getUsageToday(supabase),
    ...pets.map((p) =>
      listDiariesForPet(supabase, { petId: p.id, limit: ROW_DIARY_LIMIT }),
    ),
  ]);

  const allDiaries: Diary[] = rows.flatMap((r) => r.items);
  const heroPhotos = [...allDiaries]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 4);
  const totalDiaries = allDiaries.length;
  const oldestPet = pets[0];
  const daysWith = oldestPet ? daysTogether(oldestPet.created_at) : 0;
  const heroDate = HERO_DATE_FMT.format(new Date()).replace(/\//g, ".");

  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />

      {pets.length === 0 ? (
        <EmptyStateCard />
      ) : (
        <>
          {/* Hero — deep section, 풀블리드 */}
          <section className="bg-deep text-background py-20 px-6 sm:px-10 lg:py-32">
            <div className="mx-auto grid max-w-[1600px] grid-cols-1 gap-10 lg:grid-cols-12 lg:items-center">
              <div className="lg:col-span-8">
                <div className="mb-8 flex items-center gap-3 text-sm tracking-[0.3em] text-accent uppercase">
                  <span className="h-px w-8 bg-accent" />
                  <span>Today&apos;s Diary · {heroDate} · {displayName}님</span>
                </div>
                <h1
                  className="font-display text-5xl leading-[0.95] sm:text-6xl lg:text-[5.5rem]"
                  style={{ letterSpacing: "-0.02em" }}
                >
                  오늘 우리 아이의<br />
                  <span className="text-accent">하루</span>를 기록하세요
                </h1>
                <p className="mt-8 text-lg leading-relaxed text-background/70 sm:mt-10 sm:text-xl">
                  반려동물 사진 한 장과 키워드 한 줄로,<br />
                  1인칭 시점의 따뜻한 일기가 자동으로 완성돼요.
                </p>
                {/* Stat strip */}
                <div className="mt-12 flex gap-12 border-t border-background/20 pt-10 sm:gap-16">
                  <div>
                    <div className="font-display text-6xl sm:text-7xl">
                      {pets.length}
                    </div>
                    <div className="mt-3 text-base text-background/60">
                      함께하는 친구
                    </div>
                  </div>
                  <div>
                    <div className="font-display text-6xl sm:text-7xl">
                      {totalDiaries}
                    </div>
                    <div className="mt-3 text-base text-background/60">
                      기록된 일기
                    </div>
                  </div>
                  <div>
                    <div className="font-display text-6xl sm:text-7xl">
                      {daysWith.toLocaleString("ko-KR")}
                    </div>
                    <div className="mt-3 text-base text-background/60">
                      함께한 날
                    </div>
                  </div>
                </div>
              </div>

              {/* Photo collage 2x2 — 최근 일기 사진 */}
              <div className="lg:col-span-4">
                <div className="mx-auto grid max-w-md grid-cols-2 gap-3 lg:max-w-none">
                  {[0, 1, 2, 3].map((slot) => {
                    const photo = heroPhotos[slot];
                    if (photo) {
                      return (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          key={photo.id}
                          src={photo.photo_signed_url}
                          alt={photo.short_caption}
                          className="aspect-square w-full rounded-md object-cover"
                        />
                      );
                    }
                    // 빈 슬롯 — accent 박스 + 이모지
                    const isAccent = slot === 2;
                    return (
                      <div
                        key={`empty-${slot}`}
                        className={cn(
                          "aspect-square w-full rounded-md flex items-center justify-center",
                          isAccent
                            ? "bg-accent text-foreground"
                            : "bg-deep-soft border border-deep-border",
                        )}
                      >
                        {isAccent ? (
                          <span className="font-display text-5xl">🐱🐶</span>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>

          {/* Pet rows — 색블록 교차 (light/deep-soft) */}
          {pets.map((pet, i) => {
            const variant = i % 2 === 0 ? "light" : "deep";
            const isDeep = variant === "deep";
            return (
              <section
                key={pet.id}
                className={cn(
                  "px-6 py-20 sm:px-10 lg:py-24",
                  isDeep
                    ? "bg-deep-soft text-background"
                    : "bg-background text-foreground",
                )}
              >
                <div className="mx-auto max-w-[1600px]">
                  <PetRow
                    pet={pet}
                    diaries={rows[i].items}
                    newRemaining={usage.new_remaining}
                    index={i + 1}
                    variant={variant}
                  />
                </div>
              </section>
            );
          })}

          {/* + 새 펫 추가 CTA */}
          <section className="bg-background px-6 py-20 sm:px-10 lg:py-24">
            <div className="mx-auto max-w-3xl text-center">
              <div className="mb-4 flex items-center justify-center gap-3 text-xs tracking-[0.3em] text-muted-foreground uppercase">
                <span className="h-px w-8 bg-muted-foreground" />
                <span>Add Another Friend</span>
                <span className="h-px w-8 bg-muted-foreground" />
              </div>
              <h2
                className="font-display text-4xl leading-tight sm:text-5xl"
                style={{ letterSpacing: "-0.02em" }}
              >
                또 다른 가족이<br />
                있다면요?
              </h2>
              <p className="mt-5 text-base leading-relaxed text-muted-foreground">
                반려동물 정보를 추가하면 그 친구만의 일기 row가 메인에 생겨요.
              </p>
              <Link
                href="/pets/new"
                className={buttonVariants({
                  size: "lg",
                  className:
                    "mt-10 bg-primary text-primary-foreground hover:bg-primary/80 px-10 h-12 rounded-md text-base font-medium",
                })}
              >
                + 새 펫 추가하기
              </Link>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
