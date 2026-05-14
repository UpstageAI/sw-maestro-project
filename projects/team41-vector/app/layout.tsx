// ─── 루트 레이아웃 ───
// Next.js App Router의 최상위 레이아웃. 모든 페이지에 적용된다.
// 폰트(Geist), 메타데이터, globals.css를 여기서 세팅한다.

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

// Geist Sans: 본문 폰트 (CSS 변수 --font-geist-sans)
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

// Geist Mono: 코드/숫자 폰트 (CSS 변수 --font-geist-mono)
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "팩폭머니 — AI 재정 코치",
  description: "소비 데이터 기반 AI 팩폭 재정 코칭",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    // light 고정: 다크모드 미지원. h-full: 100dvh 레이아웃을 위해 html도 full-height.
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} light h-full antialiased`}
    >
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
