'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { setPendingSignup, isLoggedIn } from '../_lib/auth'

type StepId = 'name' | 'email' | 'password' | 'department' | 'grade'

interface FormValues {
  name: string
  email: string
  password: string
  department: string
  grade: string
}

const DEPARTMENTS = [
  '컴퓨터공학과', '소프트웨어학부', '전자공학과', '정보통신공학과',
  '기계공학과', '경영학과', '경제학과', '수학과', '물리학과', '기타',
]

const GRADES = ['1학년', '2학년', '3학년', '4학년']

const STEP_LABELS: Record<StepId, string> = {
  name: '이름',
  email: '이메일',
  password: '비밀번호',
  department: '학과',
  grade: '학년',
}

const STEP_QUESTIONS: Record<StepId, string> = {
  name: '이름이 무엇인가요?',
  email: '학교 이메일을 알려주세요',
  password: '비밀번호를 설정해주세요',
  department: '어떤 학과인가요?',
  grade: '몇 학년인가요?',
}

const STEP_ORDER: StepId[] = ['name', 'email', 'password', 'department', 'grade']
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const ease = [0.22, 1, 0.36, 1] as const

export default function SignupPage() {
  const router = useRouter()
  const [stepIndex, setStepIndex] = useState(0)
  const [values, setValues] = useState<FormValues>({ name: '', email: '', password: '', department: '', grade: '' })
  const [tempInput, setTempInput] = useState('')
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const currentStepId = STEP_ORDER[stepIndex]

  useEffect(() => {
    if (isLoggedIn()) {
      router.replace('/feed')
    }
  }, [router])

  useEffect(() => {
    const isTextField = currentStepId === 'name' || currentStepId === 'email' || currentStepId === 'password'
    if (isTextField) {
      const t = setTimeout(() => inputRef.current?.focus(), 480)
      return () => clearTimeout(t)
    }
    setError('')
  }, [currentStepId])

  function goToStep(idx: number) {
    const stepId = STEP_ORDER[idx]
    setError('')
    setStepIndex(idx)
    const isTextField = stepId === 'name' || stepId === 'email' || stepId === 'password'
    setTempInput(isTextField ? values[stepId] : '')
  }

  function validate(): boolean {
    if (!tempInput.trim()) return false
    if (currentStepId === 'email') {
      if (!EMAIL_REGEX.test(tempInput.trim())) {
        setError('올바른 이메일 형식으로 입력해주세요 (예: example@khu.ac.kr)')
        return false
      }
    }
    if (currentStepId === 'password') {
      if (tempInput.length < 8) {
        setError('비밀번호는 8자 이상이어야 해요')
        return false
      }
    }
    return true
  }

  function advance(stepId: StepId, value: string) {
    const updated = { ...values, [stepId]: value }
    setValues(updated)
    setTempInput('')
    setError('')
    if (stepIndex + 1 >= STEP_ORDER.length) {
      setPendingSignup(updated)
      router.push('/interests?signup=true')
    } else {
      setStepIndex(prev => prev + 1)
    }
  }

  function handleTextNext() {
    if (!validate()) return
    advance(currentStepId, tempInput.trim())
  }

  return (
    <div className="mx-auto max-w-lg">
      <div className="overflow-hidden rounded-3xl border border-indigo-100 bg-white/80 shadow-xl shadow-indigo-100/50 backdrop-blur-sm">

        {/* Gradient header */}
        <div className="relative overflow-hidden bg-gradient-to-r from-indigo-600 to-violet-500 px-8 pt-8 pb-6">
          <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl" />
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-200">
            회원가입
          </p>
          <p className="text-xl font-bold text-white">
            {stepIndex < STEP_ORDER.length ? STEP_QUESTIONS[currentStepId] : '완료!'}
          </p>

          {/* Progress dots */}
          <div className="mt-5 flex items-center gap-2">
            {STEP_ORDER.map((_, i) => (
              <motion.div
                key={i}
                animate={{
                  width: i === stepIndex ? 24 : 8,
                  backgroundColor: i <= stepIndex ? '#ffffff' : 'rgba(255,255,255,0.3)',
                }}
                transition={{ duration: 0.35, ease: 'easeOut' }}
                className="h-2 rounded-full"
              />
            ))}
            <span className="ml-auto text-xs font-medium text-indigo-200">
              {stepIndex + 1} / {STEP_ORDER.length}
            </span>
          </div>
        </div>

        {/* Form body */}
        <div className="px-8 py-7">
          <div className="flex flex-col">
            {STEP_ORDER.slice(0, stepIndex + 1).map((stepId, idx) => {
              const isActive = idx === stepIndex
              return (
                <motion.div
                  key={stepId}
                  initial={{ opacity: 0, y: 40 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.48, ease }}
                >
                  <AnimatePresence mode="wait" initial={false}>
                    {isActive ? (
                      <motion.div
                        key="active"
                        exit={{ opacity: 0, y: -20, transition: { duration: 0.18 } }}
                        className="py-2"
                      >
                        {(stepId === 'name' || stepId === 'email' || stepId === 'password') && (
                          <div className="flex flex-col gap-4">
                            <div className="flex flex-col gap-1.5">
                              <input
                                ref={inputRef}
                                type={
                                  stepId === 'email' ? 'email' :
                                  stepId === 'password' ? 'password' :
                                  'text'
                                }
                                placeholder={
                                  stepId === 'name' ? '홍길동' :
                                  stepId === 'email' ? 'example@khu.ac.kr' :
                                  '비밀번호를 8자 이상 입력해주세요'
                                }
                                value={tempInput}
                                onChange={e => { setTempInput(e.target.value); setError('') }}
                                onKeyDown={e => e.key === 'Enter' && handleTextNext()}
                                className="border-b-2 border-indigo-100 bg-transparent pb-2 text-2xl font-medium text-zinc-900 placeholder:text-zinc-200 focus:border-indigo-500 focus:outline-none transition-colors duration-200"
                              />
                              <AnimatePresence>
                                {error && (
                                  <motion.p
                                    initial={{ opacity: 0, y: -4 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    className="text-xs font-medium text-red-500"
                                  >
                                    {error}
                                  </motion.p>
                                )}
                              </AnimatePresence>
                            </div>
                            <AnimatePresence>
                              {tempInput.trim() && (
                                <motion.button
                                  initial={{ opacity: 0, y: 12 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  exit={{ opacity: 0, y: 8 }}
                                  transition={{ duration: 0.2 }}
                                  onClick={handleTextNext}
                                  whileTap={{ scale: 0.96 }}
                                  className="self-start rounded-xl bg-gradient-to-r from-indigo-600 to-violet-500 px-8 py-3 text-sm font-bold text-white shadow-md shadow-indigo-200 hover:opacity-90 transition-opacity"
                                >
                                  다음 →
                                </motion.button>
                              )}
                            </AnimatePresence>
                          </div>
                        )}

                        {stepId === 'department' && (
                          <motion.div
                            className="grid grid-cols-2 gap-2"
                            initial="hidden"
                            animate="show"
                            variants={{ show: { transition: { staggerChildren: 0.04 } } }}
                          >
                            {DEPARTMENTS.map(dept => (
                              <motion.button
                                key={dept}
                                variants={{
                                  hidden: { opacity: 0, y: 14 },
                                  show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: 'easeOut' } },
                                }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => advance(stepId, dept)}
                                className="rounded-xl border border-zinc-100 bg-zinc-50 px-4 py-3.5 text-sm font-medium text-zinc-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 transition-all text-left"
                              >
                                {dept}
                              </motion.button>
                            ))}
                          </motion.div>
                        )}

                        {stepId === 'grade' && (
                          <motion.div
                            className="grid grid-cols-2 gap-3"
                            initial="hidden"
                            animate="show"
                            variants={{ show: { transition: { staggerChildren: 0.07 } } }}
                          >
                            {GRADES.map(grade => (
                              <motion.button
                                key={grade}
                                variants={{
                                  hidden: { opacity: 0, y: 14 },
                                  show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: 'easeOut' } },
                                }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => advance(stepId, grade)}
                                className="rounded-xl border border-zinc-100 bg-zinc-50 py-5 text-xl font-bold text-zinc-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 transition-all"
                              >
                                {grade}
                              </motion.button>
                            ))}
                          </motion.div>
                        )}
                      </motion.div>
                    ) : (
                      <motion.button
                        key="done"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.25 }}
                        onClick={() => goToStep(idx)}
                        className="w-full flex items-center justify-between border-b border-zinc-100 py-3.5 -mx-2 px-2 rounded-lg hover:bg-zinc-50 transition-colors group text-left"
                      >
                        <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">
                          {STEP_LABELS[stepId]}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-zinc-700">
                            {stepId === 'password' ? '••••••••' : values[stepId]}
                          </span>
                          <span className="text-[10px] text-zinc-300 group-hover:text-indigo-400 transition-colors">
                            수정
                          </span>
                          <motion.span
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: 'spring', stiffness: 500, damping: 22 }}
                            className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[10px] text-indigo-600"
                          >
                            ✓
                          </motion.span>
                        </div>
                      </motion.button>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>

      <p className="mt-4 text-center text-xs text-zinc-400">
        가입 후 관심사를 선택하면 맞춤 알림을 받을 수 있어요
      </p>
      <p className="mt-2 text-center text-sm text-zinc-500">
        이미 계정이 있으신가요?{' '}
        <Link href="/login" className="font-semibold text-indigo-600 hover:underline">
          로그인
        </Link>
      </p>
    </div>
  )
}
