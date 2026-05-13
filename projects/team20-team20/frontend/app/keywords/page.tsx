'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { isLoggedIn, getUserId } from '../_lib/auth'

const SUGGESTIONS = ['등록금', '수강신청', '현장실습', '교환학생', '복학', '휴학', '취업특강', '공모전', '봉사활동', '기숙사']

const KEYWORD_COLORS = [
  'from-violet-500 to-indigo-500',
  'from-blue-500 to-cyan-400',
  'from-indigo-500 to-blue-500',
  'from-emerald-500 to-teal-400',
  'from-amber-500 to-orange-400',
  'from-pink-500 to-rose-400',
]

export default function KeywordsPage() {
  const router = useRouter()
  const [keywords, setKeywords] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [fetching, setFetching] = useState(true)
  const [pending, setPending] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!isLoggedIn()) { router.replace('/login'); return }
    const uid = getUserId()
    if (!uid) return
    fetch(`/api/users/${uid}/interests`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.interests && Array.isArray(data.interests)) {
          setKeywords(data.interests)
        }
      })
      .catch(() => {})
      .finally(() => setFetching(false))
  }, [router])

  async function addKeyword(kw?: string) {
    const trimmed = (kw ?? input).trim()
    if (!trimmed || loading) return
    if (userId == null) { setError('회원가입을 먼저 완료해주세요.'); return }
    if (keywords.includes(trimmed)) { setError('이미 추가된 키워드예요'); return }
    if (keywords.length >= 20) { setError('최대 20개까지 추가할 수 있어요'); return }
    if (pending.has(trimmed)) return

    const uid = getUserId()
    if (!uid) return
    setPending(prev => new Set([...prev, trimmed]))
    setError('')
    try {
      const res = await fetch(`/api/users/${uid}/interests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interest_text: trimmed }),
      })
      if (!res.ok) throw new Error('키워드 추가에 실패했어요.')
      setKeywords(prev => [...prev, trimmed])
      setInput('')
    } catch (e) {
      setError(e instanceof Error ? e.message : '오류가 발생했어요.')
    } finally {
      setPending(prev => { const n = new Set(prev); n.delete(trimmed); return n })
    }
  }

  async function removeKeyword(kw: string) {
    if (pending.has(kw)) return
    const uid = getUserId()
    if (!uid) return
    setPending(prev => new Set([...prev, kw]))
    setError('')
    try {
      const res = await fetch(`/api/users/${uid}/interests/${encodeURIComponent(kw)}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('키워드 삭제에 실패했어요.')
      setKeywords(prev => prev.filter(k => k !== kw))
    } catch (e) {
      setError(e instanceof Error ? e.message : '오류가 발생했어요.')
    } finally {
      setPending(prev => { const n = new Set(prev); n.delete(kw); return n })
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      {/* Header */}
      <div className="mb-8">
        <p className="mb-1 text-xs font-bold uppercase tracking-widest text-indigo-400">키워드 관리</p>
        <h1 className="text-3xl font-extrabold text-zinc-900">내 키워드</h1>
        <p className="mt-1 text-sm text-zinc-500">등록한 키워드가 포함된 공지를 우선 알려드려요</p>
      </div>

      {/* Input */}
      <div className="mb-6 overflow-hidden rounded-2xl border border-zinc-100 bg-white shadow-sm">
        <div className="border-b border-zinc-50 bg-gradient-to-r from-indigo-50 to-violet-50 px-5 py-4">
          <p className="text-sm font-bold text-zinc-900">키워드 추가</p>
        </div>
        <div className="p-5">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="키워드 입력 후 Enter"
              value={input}
              onChange={e => { setInput(e.target.value); setError('') }}
              onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addKeyword())}
              maxLength={30}
              className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2.5 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-200 transition-all"
            />
            <motion.button
              onClick={() => addKeyword()}
              disabled={!input.trim() || pending.has(input.trim())}
              whileTap={{ scale: 0.94 }}
              className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-500 px-5 py-2.5 text-sm font-bold text-white shadow-sm shadow-indigo-200 hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              {pending.has(input.trim()) ? '⋯' : '추가'}
            </motion.button>
          </div>
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-2 text-xs font-medium text-red-500"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>

          {/* Suggestions */}
          <div className="mt-4">
            <p className="mb-2 text-xs font-semibold text-zinc-400">추천 키워드</p>
            <div className="flex flex-wrap gap-1.5">
              {SUGGESTIONS.filter(s => !keywords.includes(s)).map(ex => (
                <button
                  key={ex}
                  onClick={() => addKeyword(ex)}
                  disabled={pending.has(ex)}
                  className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-500 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600 transition-all disabled:opacity-40"
                >
                  {pending.has(ex) ? '⋯' : `+ ${ex}`}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Keywords display */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm font-bold text-zinc-700">
            등록된 키워드
            <span className="ml-2 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-bold text-indigo-600">
              {keywords.length}
            </span>
          </p>
          <p className="text-xs text-zinc-400">최대 20개</p>
        </div>

        {fetching ? (
          <div className="rounded-2xl border border-zinc-100 bg-white py-14 text-center">
            <p className="text-sm text-zinc-400">불러오는 중...</p>
          </div>
        ) : keywords.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-200 bg-white py-14 text-center">
            <p className="text-2xl">🔍</p>
            <p className="mt-2 text-sm font-medium text-zinc-400">키워드를 추가해 보세요</p>
            <p className="mt-1 text-xs text-zinc-300">위에서 원하는 키워드를 입력하거나 선택하세요</p>
          </div>
        ) : (
          <motion.ul layout className="flex flex-wrap gap-2">
            <AnimatePresence>
              {keywords.map((kw, idx) => {
                const gradient = KEYWORD_COLORS[idx % KEYWORD_COLORS.length]
                return (
                  <motion.li
                    key={kw}
                    layout
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-center gap-2 rounded-xl bg-white border border-zinc-100 shadow-sm pl-1 pr-3 py-1"
                  >
                    <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${gradient} text-[10px] font-bold text-white`}>
                      {kw.charAt(0)}
                    </span>
                    <span className="text-sm font-semibold text-zinc-700">{kw}</span>
                    <button
                      onClick={() => removeKeyword(kw)}
                      disabled={pending.has(kw)}
                      aria-label={`${kw} 삭제`}
                      className="ml-1 flex h-4 w-4 items-center justify-center rounded-full text-zinc-300 hover:bg-red-100 hover:text-red-500 transition-colors text-xs disabled:opacity-40"
                    >
                      {pending.has(kw) ? '⋯' : '×'}
                    </button>
                  </motion.li>
                )
              })}
            </AnimatePresence>
          </motion.ul>
        )}

        {/* Progress bar */}
        {keywords.length > 0 && (
          <div className="mt-5">
            <div className="mb-1.5 flex justify-between text-xs text-zinc-400">
              <span>{keywords.length}개 사용 중</span>
              <span>20개 한도</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-zinc-100 overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
                initial={{ width: 0 }}
                animate={{ width: `${(keywords.length / 20) * 100}%` }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
