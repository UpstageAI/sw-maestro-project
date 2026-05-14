"use client";

import Link from "next/link";

type BottomNavItem = {
  id: "home" | "chat" | "report";
  href: string;
  label: string;
  visualLabel?: string;
};

type BottomNavProps = {
  active: BottomNavItem["id"];
  today?: Date;
};

function getDefaultToday() {
  return new Date();
}

function getSeoulDateString(date: Date) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));

  return `${values.year}-${values.month}-${values.day}`;
}

function getItems(today: Date): BottomNavItem[] {
  return [
    { id: "home", href: "/feed", label: "홈" },
    { id: "chat", href: "/chat", label: "챗" },
    {
      id: "report",
      href: `/report/${getSeoulDateString(today)}`,
      label: "오늘 리포트",
      visualLabel: "리포트",
    },
  ];
}

function HomeIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-[22px] w-[22px]"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      viewBox="0 0 24 24"
    >
      <path d="m3 11 9-8 9 8" />
      <path d="M5 10v10h14V10" />
      <path d="M10 20v-6h4v6" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-[22px] w-[22px]"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      viewBox="0 0 24 24"
    >
      <path d="M4 6h16a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-7l-5 4v-4H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z" />
    </svg>
  );
}

function ReportIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-[22px] w-[22px]"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      viewBox="0 0 24 24"
    >
      <path d="M6 3h12v18H6z" />
      <path d="M9 8h6" />
      <path d="M9 12h6" />
      <path d="M9 16h4" />
    </svg>
  );
}

function NavIcon({ id }: { id: BottomNavItem["id"] }) {
  if (id === "home") {
    return <HomeIcon />;
  }

  if (id === "chat") {
    return <ChatIcon />;
  }

  return <ReportIcon />;
}

export function BottomNav({ active, today = getDefaultToday() }: BottomNavProps) {
  const items = getItems(today);

  return (
    <nav
      aria-label="하단 네비게이션"
      className="grid grid-cols-[1fr_64px_1fr] items-center gap-1.5 border-t border-line bg-white/95 px-[18px] pb-[18px] pt-2.5"
    >
      {items.map((item) => {
        const isActive = active === item.id;
        const isChat = item.id === "chat";

        return (
          <Link
            key={item.id}
            href={item.href}
            aria-label={item.label}
            aria-current={isActive ? "page" : undefined}
            className={
              isChat
                ? "mx-auto -mt-1.5 flex h-[52px] w-[52px] transform-gpu items-center justify-center rounded-full bg-brand-500 text-white shadow-[0_4px_14px_rgba(255,138,61,0.38)] transition-[transform,box-shadow,background-color] duration-200 ease-out hover:-translate-y-0.5 active:translate-y-[2px] active:shadow-[0_2px_8px_rgba(255,138,61,0.3)]"
                : `flex min-h-[52px] flex-col items-center justify-center gap-1 rounded-2xl px-1 py-[7px] text-[12px] font-[750] transition-colors ${
                    isActive ? "bg-brand-50 text-brand-500" : "text-hint active:bg-chip"
                  }`
            }
          >
            <NavIcon id={item.id} />
            {!isChat ? <span>{item.visualLabel ?? item.label}</span> : null}
          </Link>
        );
      })}
    </nav>
  );
}
