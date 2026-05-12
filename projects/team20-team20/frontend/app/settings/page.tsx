'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { isLoggedIn, isOnboarded, setOnboarded } from '../_lib/auth'

type Frequency = 'realtime' | 'daily' | 'weekly'

const FREQUENCIES: { value: Frequency; label: string; desc: string; icon: string; gradient: string }[] = [
  { value: 'realtime', label: '실시간', desc: '공지가 올라오는 즉시 알림', icon: '⚡', gradient: 'from-amber-400 to-orange-400' },
  { value: 'daily',    label: '하루 1회', desc: '매일 오전 9시에 모아서 알림', icon: '☀️', gradient: 'from-indigo-400 to-blue-400' },
  { value: 'weekly',   label: '주 1회', desc: '매주 월요일에 모아서 알림', icon: '📅', gradient: 'from-violet-400 to-purple-400' },
]

export default function SettingsPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [frequency, setFrequency] = useState<Frequency>('daily')
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [userId, setUserId] = useState<number | null>(null)

  useEffect(() => {
    const uid = getUserId()
    setUserId(uid)
    if (uid == null) {
      // 세션 없으면 LS의 signup 이메일이라도 채워두기
      setEmail(getEmail() ?? '')
      return
    }
    getSettings(uid)
      .then(s => {
        setEmail(s.email)
        setFrequency(s.notification_frequency)
      })
      .catch(e => setError(e instanceof Error ? e.message : '설정 로드 실패'))
  }, [])

  useEffect(() => {
    if (!isLoggedIn()) router.replace('/login')
  }, [router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (userId == null) {
      setError('회원가입을 먼저 완료해주세요.')
      return
    }
    setLoading(true)
    setSaved(false)
    await new Promise(r => setTimeout(r, 500))
    // TODO: PATCH /api/users/notification-settings
    const firstTime = !isOnboarded()
    setOnboarded()
    setSaved(true)
    setLoading(false)
    if (firstTime) {
      await new Promise(r => setTimeout(r, 800))
      router.push('/feed')
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      {/* Header */}
      <div className="mb-8">
        <p className="mb-1 text-xs font-bold uppercase tracking-widest text-indigo-400">설정</p>
        <h1 className="text-3xl font-extrabold text-zinc-900">알림 설정</h1>
        <p className="mt-1 text-sm text-zinc-500">알림 받을 채널과 빈도를 설정하세요</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {/* Email section */}
        <section className="overflow-hidden rounded-2xl border border-zinc-100 bg-white shadow-sm">
          <div className="border-b border-zinc-50 bg-gradient-to-r from-indigo-50 to-violet-50 px-5 py-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-sm shadow-sm">
                📧
              </span>
              <div>
                <p className="text-sm font-bold text-zinc-900">알림 이메일</p>
                <p className="text-xs text-zinc-500">알림을 받을 이메일 주소</p>
              </div>
            </div>
          </div>
          <div className="p-5">
            <input
              type="email"
              required
              placeholder="example@khu.ac.kr"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-200 transition-all"
            />
          </div>
        </section>

        {/* Frequency section */}
        <section className="overflow-hidden rounded-2xl border border-zinc-100 bg-white shadow-sm">
          <div className="border-b border-zinc-50 bg-gradient-to-r from-indigo-50 to-violet-50 px-5 py-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-sm shadow-sm">
                🔔
              </span>
              <div>
                <p className="text-sm font-bold text-zinc-900">알림 빈도</p>
                <p className="text-xs text-zinc-500">얼마나 자주 받을지 선택하세요</p>
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-2.5 p-5">
            {FREQUENCIES.map(({ value, label, desc, icon, gradient }) => {
              const active = frequency === value
              return (
                <motion.label
                  key={value}
                  whileTap={{ scale: 0.98 }}
                  className={`flex cursor-pointer items-center gap-4 rounded-xl border p-4 transition-all duration-150 ${
                    active
                      ? 'border-indigo-300 bg-indigo-50 shadow-sm shadow-indigo-100'
                      : 'border-zinc-100 hover:border-zinc-200 hover:bg-zinc-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="frequency"
                    value={value}
                    checked={active}
                    onChange={() => setFrequency(value)}
                    className="sr-only"
                  />
                  <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${gradient} text-lg shadow-sm`}>
                    {icon}
                  </span>
                  <div className="flex-1">
                    <p className={`text-sm font-bold ${active ? 'text-indigo-700' : 'text-zinc-800'}`}>{label}</p>
                    <p className="text-xs text-zinc-400 mt-0.5">{desc}</p>
                  </div>
                  <motion.div
                    animate={{
                      backgroundColor: active ? '#4f46e5' : 'transparent',
                      borderColor: active ? '#4f46e5' : '#d1d5db',
                    }}
                    className="h-5 w-5 rounded-full border-2 flex items-center justify-center"
                  >
                    {active && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="h-2 w-2 rounded-full bg-white"
                      />
                    )}
                  </motion.div>
                </motion.label>
              )
            })}
          </div>
        </section>

        {/* Submit */}
        <motion.button
          type="submit"
          disabled={loading || !email}
          whileTap={{ scale: 0.97 }}
          className="rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-500 py-4 text-base font-bold text-white shadow-lg shadow-indigo-200 disabled:opacity-40 hover:opacity-90 transition-opacity"
        >
          {loading ? '저장 중...' : '설정 저장'}
        </motion.button>

        <AnimatePresence>
          {saved && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex items-center justify-center gap-2 rounded-2xl border border-emerald-100 bg-emerald-50 py-3 text-sm font-semibold text-emerald-600"
            >
              ✓ 설정이 저장되었습니다
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <p className="text-center text-xs font-medium text-red-500">{error}</p>
        )}
      </form>
    </div>
  )
}
