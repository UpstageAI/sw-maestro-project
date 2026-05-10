"use client";

import { cn } from "@/lib/utils";
import { Icon } from "@/components/chrome/icon";

interface Props {
  who: "interviewer" | "user";
  children: React.ReactNode;
}

export function MessageBubble({ who, children }: Props) {
  const isUser = who === "user";
  return (
    <div
      className={cn(
        "flex gap-md",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      {/* Avatar */}
      <div className="shrink-0">
        <span
          className={cn(
            "h-10 w-10 rounded-full flex items-center justify-center",
            isUser
              ? "bg-rausch text-on-primary"
              : "bg-ink text-on-dark",
          )}
        >
          <Icon
            name={isUser ? "person" : "psychology_alt"}
            size={20}
            filled
          />
        </span>
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "max-w-[80%] flex flex-col gap-sm",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
            "flex items-center gap-sm",
            isUser && "flex-row-reverse",
          )}
        >
          <span className="text-caption-sm text-muted">
            {isUser ? "나의 답변" : "TailQuest 면접관"}
          </span>
        </div>

        <div
          className={cn(
            "rounded-md p-lg shadow-airbnb",
            isUser ? "bg-rausch text-on-primary" : "bg-canvas border border-hairline",
          )}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
