import type { Metadata } from "next";
import { Geist_Mono, Noto_Sans_KR, Noto_Serif_KR } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SiteHeader } from "@/components/site/header";
import { SiteFooter } from "@/components/site/footer";
import "./globals.css";

const sans = Noto_Sans_KR({
  variable: "--font-pretendard",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  display: "swap",
});

const serif = Noto_Serif_KR({
  variable: "--font-display-serif",
  subsets: ["latin"],
  weight: ["500", "700", "900"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://soma17-ai17-main-project.vercel.app"),
  title: {
    default: "사장님메이트 — 사장님을 위한 인스타 카드뉴스 스튜디오",
    template: "%s · 사장님메이트",
  },
  description:
    "사진 한 장과 가게 이야기만 입력하면, 인스타 카드뉴스용 홍보물을 30초 안에 완성합니다. 소상공인을 위한 실전 디자인 어시스턴트.",
  openGraph: {
    title: "사장님메이트 (bossmate) — 사장님을 위한 인스타 카드뉴스 스튜디오",
    description:
      "사진 + 가게 정보 → 인스타 카드뉴스 자동 완성. 다운로드까지 30초.",
    type: "website",
    locale: "ko_KR",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="ko"
      suppressHydrationWarning
      className={`${sans.variable} ${serif.variable} ${geistMono.variable}`}
    >
      <body className="min-h-dvh bg-background text-foreground antialiased">
        <TooltipProvider delayDuration={120}>
          <div className="relative flex min-h-dvh flex-col">
            <SiteHeader />
            <main className="flex-1">{children}</main>
            <SiteFooter />
          </div>
          <Toaster richColors position="top-center" />
        </TooltipProvider>
      </body>
    </html>
  );
}
