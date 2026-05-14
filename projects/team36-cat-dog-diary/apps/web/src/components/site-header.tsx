// 모든 인증 페이지에서 동일 헤더 — async server component로 user/profile/첫 펫 자체 fetch.
// 호출 측은 단순 `<SiteHeader />` 한 줄.

import Link from "next/link";
import { BrandLogo } from "@/components/brand-logo";
import { HeaderUserMenu } from "@/components/header-user-menu";
import { NavLink } from "@/components/nav-link";
import { getCurrentUser } from "@/lib/server/auth";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function SiteHeader() {
  const user = await getCurrentUser();
  if (!user) return null;

  const supabase = await createSupabaseServerClient();
  const { data: profileData } = await supabase
    .from("profiles")
    .select("display_name")
    .eq("id", user.id)
    .maybeSingle();

  const displayName =
    (profileData as { display_name?: string } | null)?.display_name ??
    user.email ??
    "사용자";

  return (
    <header className="w-full border-b border-border/40 bg-card/70">
      {/* grid 3-cols 균등 — nav가 viewport 정중앙. flex justify-between은 좌/우 자식 width
          가 다르면 가운데 자식이 정중앙에 오지 않아 우측 치우침이 생김.
          각 자식에 col-start 고정 — sm 미만에서 nav가 display:none일 때 auto-flow가
          dropdown을 col 2로 당겨오는 문제 방지. */}
      <div className="mx-auto grid w-full max-w-[1600px] grid-cols-3 items-center gap-3 px-6 py-6 sm:px-10">
        <Link
          href="/"
          className="col-start-1 flex shrink-0 items-center gap-3 whitespace-nowrap text-primary justify-self-start"
        >
          <BrandLogo className="size-11" />
          <span
            className="text-2xl tracking-tight text-foreground"
            style={{
              fontFamily: "Cafe24SsurroundAir, var(--font-pretendard)",
              fontWeight: 600,
            }}
          >
            냥멍일기
          </span>
        </Link>

        <nav className="col-start-2 hidden items-center gap-10 text-lg justify-self-center sm:flex">
          <NavLink href="/" matchPath="/">
            메인
          </NavLink>
          <NavLink href="/pets/new" matchPath="/pets/new">
            새 펫
          </NavLink>
        </nav>

        <div className="col-start-3 justify-self-end">
          <HeaderUserMenu displayName={displayName} email={user.email ?? ""} />
        </div>
      </div>
    </header>
  );
}
