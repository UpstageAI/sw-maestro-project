'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import { isLoggedIn, getUser, logout, type User } from '../_lib/auth'

const NAV_LINKS = [
  { href: '/feed', label: '공지 피드' },
  { href: '/keywords', label: '키워드' },
  { href: '/settings', label: '알림 설정' },
]

export default function Navbar() {
  const pathname = usePathname()
  const router = useRouter()
  const [loggedIn, setLoggedIn] = useState(false)
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    setLoggedIn(isLoggedIn())
    setUser(getUser())
  }, [pathname])

  function handleLogout() {
    logout()
    router.push('/')
  }

  return (
    <header className="sticky top-0 z-50 border-b border-indigo-100/60 bg-white/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3.5">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-violet-500 text-sm text-white shadow-sm shadow-indigo-200">
            🔔
          </span>
          <span className="bg-gradient-to-r from-indigo-600 to-violet-500 bg-clip-text text-[15px] font-bold text-transparent">
            학교공지 AI
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {loggedIn && NAV_LINKS.map(({ href, label }) => {
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition-all duration-150 ${
                  active
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-800'
                }`}
              >
                {label}
              </Link>
            )
          })}

          {loggedIn ? (
            <div className="ml-2 flex items-center gap-2">
              <span className="rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700">
                {user?.name}
              </span>
              <button
                onClick={handleLogout}
                className="rounded-lg px-3.5 py-1.5 text-sm font-medium text-zinc-500 hover:bg-zinc-50 hover:text-zinc-800 transition-all duration-150"
              >
                로그아웃
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="ml-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-500 px-4 py-1.5 text-sm font-semibold text-white shadow-sm shadow-indigo-200 hover:opacity-90 transition-opacity"
            >
              로그인
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}
