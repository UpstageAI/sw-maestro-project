import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import Navbar from './_components/Navbar'
import './globals.css'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' })

export const metadata: Metadata = {
  title: '학교공지 AI 알림 서비스',
  description: '학과 공지를 AI가 요약해 알려드립니다',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={geist.variable}>
      <body className="min-h-screen font-sans">
        <Navbar />
        <main className="mx-auto max-w-4xl px-4 py-10">{children}</main>
      </body>
    </html>
  )
}
