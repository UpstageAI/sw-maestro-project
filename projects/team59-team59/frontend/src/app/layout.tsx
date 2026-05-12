import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HWP Editor Chatbot",
  description: "AI-powered HWPX document editor",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
