import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-5">
        <Link href="/" className="flex items-center gap-2.5">
          <Image
            src="/branding/logo-mark-512.png"
            alt="사장님메이트 로고"
            width={36}
            height={36}
            priority
            className="size-9 rounded-2xl"
          />
          <span className="flex items-baseline gap-1.5 text-base font-bold tracking-tight text-foreground">
            사장님메이트
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              bossmate
            </span>
          </span>
        </Link>
        <Button asChild size="sm" className="h-10 rounded-full px-4 text-sm font-semibold">
          <Link href="/studio">시작하기</Link>
        </Button>
      </div>
    </header>
  );
}
