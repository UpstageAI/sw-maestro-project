import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/60 bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/50">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="text-base font-semibold tracking-tight">
          면접 코치
        </Link>
        <nav className="flex items-center gap-2">
          <ThemeToggle />
          <Button
            asChild
            size="sm"
            className="rounded-full px-4 transition-transform hover:scale-105"
          >
            <Link href="/upload">Get started</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
