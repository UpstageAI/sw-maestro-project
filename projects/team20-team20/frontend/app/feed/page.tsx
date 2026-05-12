'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { isLoggedIn, getUserId } from '../_lib/auth'

type FeedbackValue = 'like' | 'dislike' | null

interface NotificationItem {
  notification_id: number
  notice_id: number
  title: string
  url: string
  source_id: string
  posted_at: string | null
  summary: string
  queued_at: string | null
  sent_at: string | null
  status: string
  feedback: FeedbackValue
}

interface NotificationListOut {
  user_id: number
  items: NotificationItem[]
}

const HOURS_OPTIONS = [
  { label: '24시간', value: 24 },
  { label: '3일', value: 72 },
  { label: '1주일', value: 168 },
]

const SOURCE_STYLE: Record<string, { badge: string; bar: string; icon: string; label: string }> = {
  // school
  snu_cse_notice:    { badge: 'bg-indigo-100 text-indigo-700 border-indigo-200',   bar: 'bg-indigo-400',  icon: '📚', label: '서울대 CSE 공지' },
  snu_cba_notice:    { badge: 'bg-violet-100 text-violet-700 border-violet-200',   bar: 'bg-violet-400',  icon: '🏛️', label: '서울대 경영대 공지' },
  // job
  saramin_hot100:    { badge: 'bg-emerald-100 text-emerald-700 border-emerald-200', bar: 'bg-emerald-400', icon: '💼', label: '사람인 HOT100' },
  naver_recruit:     { badge: 'bg-green-100 text-green-700 border-green-200',      bar: 'bg-green-500',   icon: '🟢', label: '네이버 채용' },
  jobkorea_ai:       { badge: 'bg-sky-100 text-sky-700 border-sky-200',            bar: 'bg-sky-400',     icon: '🤖', label: '잡코리아 AI 채용' },
  // community
  naver_cafe_notice: { badge: 'bg-amber-100 text-amber-700 border-amber-200',      bar: 'bg-amber-400',   icon: '☕', label: '소마 카페' },
}

const FALLBACK_COLORS = [
  { badge: 'bg-indigo-100 text-indigo-700 border-indigo-200',   bar: 'bg-indigo-400' },
  { badge: 'bg-teal-100 text-teal-700 border-teal-200',         bar: 'bg-teal-400' },
  { badge: 'bg-orange-100 text-orange-700 border-orange-200',   bar: 'bg-orange-400' },
  { badge: 'bg-rose-100 text-rose-700 border-rose-200',         bar: 'bg-rose-400' },
]

function getSourceStyle(sourceId: string) {
  if (SOURCE_STYLE[sourceId]) return SOURCE_STYLE[sourceId]
  const color = FALLBACK_COLORS[sourceId.length % FALLBACK_COLORS.length]
  return { ...color, icon: '📄', label: sourceId }
}

function formatPostedAt(postedAt: string | null): string | null {
  if (!postedAt) return null
  const d = new Date(postedAt)
  if (isNaN(d.getTime())) return null
  return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
}

export default function FeedPage() {
  const router = useRouter()
  const [hours, setHours] = useState(24)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [feedbacks, setFeedbacks] = useState<Record<number, FeedbackValue>>({})

  const fetchNotices = useCallback(async (uid: string, h: number) => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/users/${uid}/notifications?hours=${h}`)
      if (!res.ok) throw new Error('fetch failed')
      const data: NotificationListOut = await res.json()
      setItems(data.items)
      console.log(data.items)
      const init: Record<number, FeedbackValue> = {}
      data.items.forEach(item => { init[item.notification_id] = item.feedback })
      setFeedbacks(init)
    } catch {
      setError('공지를 불러오는 데 실패했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isLoggedIn()) { router.replace('/login'); return }
    const uid = getUserId()
    if (!uid) { router.replace('/login'); return }
    fetchNotices(uid, hours)
  }, [hours, router, fetchNotices])

  async function handleFeedback(notificationId: number, type: FeedbackValue) {
    const prev = feedbacks[notificationId]
    const next: FeedbackValue = prev === type ? null : type
    setFeedbacks(f => ({ ...f, [notificationId]: next }))
    try {
      await fetch(`/api/notifications/${notificationId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: next }),
      })
    } catch {
      setFeedbacks(f => ({ ...f, [notificationId]: prev }))
    }
  }

  const hoursLabel = HOURS_OPTIONS.find(o => o.value === hours)?.label ?? ''

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-end justify-between">
        <div>
          <p className="mb-1 text-xs font-bold uppercase tracking-widest text-indigo-400">AI 피드</p>
          <h1 className="text-3xl font-extrabold text-zinc-900">공지 알림</h1>
          <p className="mt-1 text-sm text-zinc-500">관심사 기반으로 선별된 공지예요</p>
        </div>
        {!loading && !error && (
          <span className="rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">
            {items.length}건
          </span>
        )}
      </div>

      {/* Hours filter */}
      <div className="mb-6 flex gap-2">
        {HOURS_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => setHours(opt.value)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-all ${
              hours === opt.value
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-200'
                : 'bg-zinc-100 text-zinc-500 hover:bg-indigo-50 hover:text-indigo-600'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Loading skeleton */}
      {loading && (
        <ul className="flex flex-col gap-4">
          {[...Array(3)].map((_, i) => (
            <li key={i} className="overflow-hidden rounded-2xl border border-zinc-100 bg-white shadow-sm">
              <div className="h-1 w-full animate-pulse bg-zinc-100" />
              <div className="flex flex-col gap-3 p-5">
                <div className="flex gap-2">
                  <div className="h-5 w-16 animate-pulse rounded-full bg-zinc-100" />
                </div>
                <div className="h-5 w-3/4 animate-pulse rounded bg-zinc-100" />
                <div className="h-4 w-full animate-pulse rounded bg-zinc-50" />
                <div className="h-4 w-2/3 animate-pulse rounded bg-zinc-50" />
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="rounded-2xl border border-red-100 bg-red-50 px-6 py-8 text-center">
          <p className="text-sm font-medium text-red-600">{error}</p>
          <button
            onClick={() => { const uid = getUserId(); if (uid) fetchNotices(uid, hours) }}
            className="mt-4 rounded-xl bg-red-500 px-5 py-2 text-sm font-bold text-white hover:opacity-90 transition-opacity"
          >
            다시 시도
          </button>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && items.length === 0 && (
        <div className="rounded-2xl border border-zinc-100 bg-zinc-50 px-6 py-12 text-center">
          <p className="text-2xl">📭</p>
          <p className="mt-3 text-sm font-medium text-zinc-500">
            최근 {hoursLabel} 동안 새 공지가 없어요
          </p>
        </div>
      )}

      {/* Notice list */}
      {!loading && !error && items.length > 0 && (
        <ul className="flex flex-col gap-4">
          {items.map((item, idx) => {
            const fb = feedbacks[item.notification_id]
            const style = getSourceStyle(item.source_id)
            const dateLabel = formatPostedAt(item.posted_at)

            return (
              <motion.li
                key={item.notification_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.07, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden rounded-2xl border border-zinc-100 bg-white shadow-sm shadow-zinc-100 hover:shadow-md hover:shadow-indigo-100/50 transition-shadow"
              >
                <div className={`h-1 w-full ${style.bar}`} />
                <div className="p-5">
                  {/* Meta row */}
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="text-base">{style.icon}</span>
                    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${style.badge}`}>
                      {style.label}
                    </span>
                    {dateLabel && (
                      <span className="ml-auto text-xs text-zinc-400">{dateLabel}</span>
                    )}
                  </div>

                  {/* Title */}
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-base font-bold leading-snug text-zinc-900 hover:text-indigo-600 transition-colors"
                  >
                    {item.title}
                  </a>

                  {/* Summary */}
                  <p className="mt-2 text-sm leading-relaxed text-zinc-500">{item.summary}</p>

                  {/* Feedback */}
                  <div className="mt-4 flex items-center gap-2 border-t border-zinc-50 pt-4">
                    <span className="text-xs text-zinc-400">도움이 됐나요?</span>
                    <div className="ml-auto flex gap-2">
                      <motion.button
                        whileTap={{ scale: 0.9 }}
                        onClick={() => handleFeedback(item.notification_id, 'like')}
                        className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-sm font-medium transition-all ${
                          fb === 'like'
                            ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-200'
                            : 'bg-zinc-50 text-zinc-500 hover:bg-indigo-50 hover:text-indigo-600'
                        }`}
                      >
                        👍 <span className="hidden sm:inline">도움돼요</span>
                      </motion.button>
                      <motion.button
                        whileTap={{ scale: 0.9 }}
                        onClick={() => handleFeedback(item.notification_id, 'dislike')}
                        className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-sm font-medium transition-all ${
                          fb === 'dislike'
                            ? 'bg-red-500 text-white shadow-sm shadow-red-200'
                            : 'bg-zinc-50 text-zinc-500 hover:bg-red-50 hover:text-red-500'
                        }`}
                      >
                        👎 <span className="hidden sm:inline">별로예요</span>
                      </motion.button>
                    </div>
                  </div>
                </div>
              </motion.li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
