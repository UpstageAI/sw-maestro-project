"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

/** 클라이언트 mount 여부 — SSR/CSR 결과 차이로 인한 hydration mismatch 회피용. */
function useMounted(): boolean {
  return React.useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );
}

export function ThemeToggle() {
  const { setTheme, resolvedTheme } = useTheme();
  const mounted = useMounted();
  const isDark = mounted && resolvedTheme === "dark";

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={isDark ? "라이트 모드로 전환" : "다크 모드로 전환"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {mounted ? (
        isDark ? <Moon className="size-4" /> : <Sun className="size-4" />
      ) : (
        <Sun className="size-4 opacity-0" />
      )}
    </Button>
  );
}
