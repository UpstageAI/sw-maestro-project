'use client'

import { useState, useEffect, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter, useSearchParams } from 'next/navigation'
import { isLoggedIn, getPendingSignup, clearPendingSignup, setUser } from '../_lib/auth'

const ease = [0.22, 1, 0.36, 1] as const

function InterestsContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const isSignupFlow = searchParams.get('signup') === 'true'

  const [interestText, setInterestText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const textLength = interestText.length
  const textValid = textLength >= 1 && textLength <= 2000

  useEffect(() => {
    if (!isSignupFlow && !isLoggedIn()) router.replace('/login')
  }, [router, isSignupFlow])

  async function handleSubmit() {
    if (!textValid || loading) return
    setLoading(true)
    setError('')

    if (isSignupFlow) {
      const pending = getPendingSignup()
      if (!pending) {
        router.replace('/signup')
        return
      }

      try {
        const res = await fetch('/api/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: pending.email,
            interest_text: interestText,
          }),
        })

        if (!res.ok) throw new Error('회원가입에 실패했어요. 다시 시도해 주세요.')

        setUser(pending)
        clearPendingSignup()
        router.push('/signup/complete')
      } catch (e) {
        setError(e instanceof Error ? e.message : '오류가 발생했어요. 다시 시도해 주세요.')
        setLoading(false)
      }
    } else {
      router.push('/feed')
    }
  }

  return (
    <div className="mx-auto max-w-lg pb-36">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease }}
        className="mb-8"
      >
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3.5 py-1.5">
          <span className="text-sm">✍️</span>
          <span className="text-xs font-semibold text-indigo-600">관심사 입력</span>
        </div>
        <h1 className="text-2xl font-extrabold text-zinc-900">
          어떤 공지가<br />궁금하세요?
        </h1>
        <p className="mt-2 text-sm text-zinc-500">
          관심 있는 분야나 궁금한 내용을 자유롭게 적어주세요
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.42, delay: 0.1, ease }}
        className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm"
      >
        <textarea
          value={interestText}
          onChange={e => setInterestText(e.target.value)}
          placeholder="예: 장학금 관련 공지와 취업 정보에 관심이 많고, 교환학생 프로그램도 알고 싶어요."
          maxLength={2000}
          rows={7}
          className="w-full resize-none rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-200 transition-all"
        />
        <div className="mt-2 flex justify-end">
          <span className={`text-xs font-medium ${textLength > 2000 ? 'text-red-500' : 'text-zinc-400'}`}>
            {textLength} / 2000
          </span>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25, duration: 0.4 }}
        className="fixed bottom-0 left-0 right-0 border-t border-indigo-50 bg-white/80 p-4 backdrop-blur-xl"
      >
        <div className="mx-auto max-w-lg flex flex-col gap-2">
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-xl bg-red-50 border border-red-100 px-4 py-3 text-sm font-medium text-red-600 text-center"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>
          <motion.button
            onClick={handleSubmit}
            disabled={!textValid || loading}
            whileTap={{ scale: 0.98 }}
            className="w-full rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-500 py-4 text-base font-bold text-white shadow-lg shadow-indigo-200 disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            {loading ? '처리 중...' : '가입 완료'}
          </motion.button>
          {error && (
            <p className="mt-3 text-center text-xs font-medium text-red-500">{error}</p>
          )}
        </div>
      </motion.div>
    </div>
  )
}

export default function InterestsPage() {
  return (
    <Suspense>
      <InterestsContent />
    </Suspense>
  )
}
