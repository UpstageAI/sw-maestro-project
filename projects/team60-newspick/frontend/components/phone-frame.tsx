import type { ReactNode } from "react";

type PhoneFrameProps = {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
};

export function PhoneFrame({
  children,
  className = "",
  contentClassName = "",
}: PhoneFrameProps) {
  return (
    <section
      className={`relative flex h-[min(820px,calc(100dvh-40px))] w-full max-w-[390px] flex-col overflow-hidden rounded-phone bg-surface shadow-[0_18px_50px_rgba(25,31,40,0.12)] ${className}`}
    >
      <div className="flex min-h-12 items-start justify-between px-6 pt-3.5 text-[13px] font-bold text-ink">
        <span>9:41</span>
        <span className="text-[12px]">5G 100%</span>
      </div>

      <div className={`flex min-h-0 flex-1 flex-col ${contentClassName}`}>{children}</div>
    </section>
  );
}
