"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getToken, syncWithServerBoot } from "@/lib/auth";

/** Home is a thin router:
 *   - no user logged in   → /login
 *   - logged in           → /chat
 *
 * Client-side because we read localStorage. We first sync against the backend's
 * boot_id so a server restart wipes the cached login (back to /login). */
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    syncWithServerBoot().then(() => {
      router.replace(getToken() ? "/chat" : "/login");
    });
  }, [router]);

  return (
    <main className="flex-1 flex items-center justify-center">
      <span className="text-body-sm text-muted">불러오는 중…</span>
    </main>
  );
}
