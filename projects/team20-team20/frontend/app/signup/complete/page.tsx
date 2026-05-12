'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'

const ease = [0.22, 1, 0.36, 1] as const

export default function SignupCompletePage() {
  return (
    <div className="mx-auto max-w-lg">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease }}
        className="overflow-hidden rounded-3xl border border-indigo-100 bg-white/80 shadow-xl shadow-indigo-100/50 backdrop-blur-sm"
      >
        {/* Gradient header */}
        <div className="relative overflow-hidden bg-gradient-to-r from-indigo-600 to-violet-500 px-8 pt-10 pb-8 text-center">
          <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
          <div className="pointer-events-none absolute -left-8 -bottom-8 h-24 w-24 rounded-full bg-white/10 blur-2xl" />

          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 400, damping: 20 }}
            className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white/20 text-3xl backdrop-blur-sm"
          >
            🎉
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4, ease }}
            className="mb-1 text-xs font-semibold uppercase tracking-widest text-indigo-200"
          >
            가입 완료
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.4, ease }}
            className="text-2xl font-extrabold text-white"
          >
            회원가입이 완료됐어요!
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.45, duration: 0.4 }}
            className="mt-2 text-sm text-indigo-200"
          >
            이제 로그인하고 맞춤 공지를 받아보세요
          </motion.p>
        </div>

        {/* Body */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.4 }}
          className="flex flex-col gap-4 px-8 py-8"
        >
          <div className="flex flex-col gap-3 rounded-2xl bg-indigo-50 border border-indigo-100 px-5 py-4">
            <div className="flex items-center gap-3">
              <span className="text-lg">📬</span>
              <p className="text-sm text-zinc-600">
                선택한 키워드의 공지가 올라오면 AI가 요약해서 알려드려요
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-lg">⚙️</span>
              <p className="text-sm text-zinc-600">
                관심사는 로그인 후 설정에서 언제든 변경할 수 있어요
              </p>
            </div>
          </div>

          <Link href="/login">
            <motion.div
              whileTap={{ scale: 0.97 }}
              className="mt-2 w-full cursor-pointer rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-500 py-4 text-center text-base font-bold text-white shadow-lg shadow-indigo-200 hover:opacity-90 transition-opacity"
            >
              로그인하러 가기
            </motion.div>
          </Link>
        </motion.div>
      </motion.div>
    </div>
  )
}
