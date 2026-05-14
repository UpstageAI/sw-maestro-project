"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

interface NavLinkProps extends Omit<ComponentProps<typeof Link>, "children"> {
  /** 활성 비교에 사용할 pathname (query 제외). */
  matchPath: string;
  /** exact: pathname === matchPath / startsWith: pathname.startsWith(matchPath). 기본 exact. */
  matchType?: "exact" | "startsWith";
  children: ReactNode;
}

export function NavLink({
  matchPath,
  matchType = "exact",
  className,
  children,
  ...rest
}: NavLinkProps) {
  const pathname = usePathname();
  const isActive =
    matchType === "exact"
      ? pathname === matchPath
      : pathname.startsWith(matchPath);

  return (
    <Link
      {...rest}
      className={cn(
        "transition-colors hover:text-primary",
        isActive ? "font-bold text-foreground" : "text-muted-foreground",
        className,
      )}
    >
      {children}
    </Link>
  );
}
