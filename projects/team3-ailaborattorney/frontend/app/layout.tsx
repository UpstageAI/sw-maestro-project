import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "AI 노무사 · 근로계약서 분석",
  description: "AI가 5초 만에 근로계약서를 검토합니다.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-[var(--color-bg-page)] text-grey-900 antialiased">
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-grey-200">
          <div className="mx-auto max-w-3xl px-5 sm:px-6 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 group">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-[10px] bg-toss-blue text-white font-bold text-sm shadow-[0_2px_6px_rgba(49,130,246,0.35)]">
                AI
              </span>
              <span className="text-[15px] font-bold tracking-tight text-grey-900 group-hover:text-toss-blue transition-colors">
                AI 노무사
              </span>
            </Link>
            <Link
              href="/upload"
              className="inline-flex items-center gap-1.5 rounded-full bg-grey-900 text-white text-[13px] font-semibold px-3.5 py-1.5 hover:bg-grey-800 transition-colors"
            >
              계약서 분석
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </Link>
          </div>
        </header>

        <main className="mx-auto max-w-3xl px-5 sm:px-6 py-8 sm:py-10">
          {children}
        </main>

        <footer className="mx-auto max-w-3xl px-5 sm:px-6 pb-10 pt-6">
          <p className="text-[12px] leading-5 text-grey-500">
            본 서비스는 자동 검토 결과를 제공하며 법적 자문이 아닙니다. 정확한 판단은 노무사 또는 노동청 상담을 권합니다.
          </p>
        </footer>
      </body>
    </html>
  );
}
