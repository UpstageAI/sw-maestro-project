import type { Metadata } from "next";
import "./globals.css";
import { Footer } from "@/components/footer";
import { QueryProvider } from "@/lib/queries/QueryProvider";

export const metadata: Metadata = {
  title: "twinmatch — AI가 먼저 만나보는 소개팅",
  description: "내 분신과 상대 분신이 먼저 대화해보는 AI 소개팅",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <QueryProvider>
          <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>{children}</main>
          <Footer />
        </QueryProvider>
      </body>
    </html>
  );
}
