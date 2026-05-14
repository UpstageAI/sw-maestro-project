'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { isLoggedIn, login, setUserId } from '../_lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isLoggedIn()) {
      router.replace('/feed')
      return
    }
    const t = setTimeout(() => emailRef.current?.focus(), 200)
    return () => clearTimeout(t)
  }, [router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim() || loading) return
    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/users/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      })

      if (!res.ok) {
        setError('등록되지 않은 이메일이에요. 회원가입 후 이용해 주세요.')
        setLoading(false)
        return
      }

      const data = await res.json()
      if (data.user_id != null) setUserId(String(data.user_id))
      login()
      router.push('/feed')
    } catch {
      setError('서버 오류가 발생했어요. 잠시 후 다시 시도해 주세요.')
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        className="overflow-hidden rounded-3xl border border-indigo-100 bg-white/80 shadow-xl shadow-indigo-100/50 backdrop-blur-sm"
      >
        {/* Gradient header */}
        <div className="relative overflow-hidden bg-gradient-to-r from-indigo-600 to-violet-500 px-8 pt-8 pb-6">
          <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-200">
            학교공지 AI
          </p>
          <p className="text-2xl font-extrabold text-white">다시 만나서 반가워요!</p>
          <p className="mt-1 text-sm text-indigo-200">계정에 로그인하세요</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-6 px-8 py-8">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              이메일
            </label>
            <input
              ref={emailRef}
              type="email"
              required
              placeholder="example@khu.ac.kr"
              value={email}
              onChange={e => { setEmail(e.target.value); setError('') }}
              className="border-b-2 border-indigo-100 bg-transparent pb-2.5 text-xl font-medium text-zinc-900 placeholder:text-zinc-300 focus:border-indigo-500 focus:outline-none transition-colors duration-200"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              비밀번호
            </label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit(e as unknown as React.FormEvent)}
              className="border-b-2 border-indigo-100 bg-transparent pb-2.5 text-xl font-medium text-zinc-900 placeholder:text-zinc-300 focus:border-indigo-500 focus:outline-none transition-colors duration-200"
            />
          </div>

          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-xl bg-red-50 border border-red-100 px-4 py-3 text-sm font-medium text-red-600"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>

          <motion.button
            type="submit"
            disabled={loading || !email.trim()}
            whileTap={{ scale: 0.97 }}
            className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-500 py-4 text-sm font-bold text-white shadow-md shadow-indigo-200 disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            {loading ? '로그인 중...' : '로그인'}
          </motion.button>
        </form>
      </motion.div>

      <p className="mt-5 text-center text-sm text-zinc-500">
        처음이신가요?{' '}
        <Link href="/signup" className="font-semibold text-indigo-600 hover:underline">
          회원가입하기
        </Link>
      </p>
    </div>
  )
}
