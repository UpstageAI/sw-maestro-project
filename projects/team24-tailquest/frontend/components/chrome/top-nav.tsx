"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getToken, getUser, type AuthUser } from "@/lib/auth";
import { logout } from "@/lib/api-auth";
import { UserMenu } from "@/components/chrome/user-menu";

export function TopNav() {
  const router = useRouter();
  // Re-read auth state on every route change so logout immediately clears
  // the menu (the component doesn't unmount when handleLogout calls
  // router.replace("/login") — only the page tree under main does).
  // Storage is synchronous, so this stays cheap.
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getToken() ? getUser() : null);
  }, [pathname]);

  async function handleLogout() {
    // Optimistically blank the menu so the UI doesn't show the prior email
    // for the brief interval between logout() awaiting and the navigation
    // settling.
    setUser(null);
    await logout();
    router.replace("/login");
  }

  return (
    // Airbnb top-nav: white surface, 80px height, 1px bottom hairline.
    <header className="bg-canvas border-b border-hairline w-full z-30 sticky top-0">
      <div className="h-20 px-xl w-full flex items-center justify-between gap-lg">
        <Link
          href="/onboarding"
          className="flex items-center gap-2 shrink-0"
          aria-label="새 면접 시작 (트랙 선택)"
        >
          <span className="text-rausch text-display-md leading-none">●</span>
          <span className="text-display-sm text-ink tracking-tight">
            tailquest
          </span>
        </Link>

        {user && (
          <UserMenu email={user.email} onLogout={handleLogout} />
        )}
      </div>
    </header>
  );
}
