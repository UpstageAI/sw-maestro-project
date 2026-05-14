import type { Metadata } from "next";
import "./globals.css";

import { TopNav } from "@/components/chrome/top-nav";

export const metadata: Metadata = {
  title: "TailQuest AI — 기술 면접 꼬리질문 코칭",
  description:
    "면접 답변을 분석하고 면접관 관점의 꼬리질문을 자동 생성합니다. RAG 기반 사용자 자료 활용.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      {/* h-screen + overflow-hidden so the chat shell can run a single fixed
          viewport — no page-level scroll. */}
      <body className="bg-canvas text-ink h-screen flex flex-col overflow-hidden">
        <TopNav />
        {children}
      </body>
    </html>
  );
}
