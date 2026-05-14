// React.cache로 wrap된 server-side 인증 helper.
// 같은 request 안에서 여러 server component(예: 페이지 + SiteHeader)가 호출해도
// Supabase auth.getUser()의 외부 token verify 호출을 1회로 줄여줌. 호출 1회당 200~400ms.
//
// `getUser()`는 매번 Supabase API에 token 검증 요청을 보내는 비싼 함수다. 본 cache는
// **same request 내** dedupe만 한다 — 다른 request나 다른 page render 시엔 다시 호출됨.
//
// 미래 후속: `getClaims()`로 전환하면 외부 호출 제거(로컬 JWT 검증, ms 단위) 가능.

import { cache } from "react";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export const getCurrentUser = cache(async () => {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
});
