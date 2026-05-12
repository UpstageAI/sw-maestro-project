import Link from 'next/link'

const FEATURES = [
  {
    icon: '🎯',
    title: '관심사 맞춤',
    desc: '학과·학년·관심 키워드 기반으로 꼭 필요한 공지만 골라드려요',
    gradient: 'from-violet-500 to-indigo-500',
    bg: 'bg-violet-50',
    border: 'border-violet-100',
  },
  {
    icon: '🤖',
    title: 'AI 요약',
    desc: '긴 공지를 3줄로 요약해 빠르게 핵심만 파악할 수 있어요',
    gradient: 'from-blue-500 to-cyan-400',
    bg: 'bg-blue-50',
    border: 'border-blue-100',
  },
  {
    icon: '📬',
    title: '이메일 알림',
    desc: '실시간·하루1회·주1회 중 원하는 빈도로 알림을 받아보세요',
    gradient: 'from-indigo-500 to-blue-400',
    bg: 'bg-indigo-50',
    border: 'border-indigo-100',
  },
]

const MOCK_NOTICES = [
  { label: '장학금', title: '성적우수 장학금 신청 마감', badge: 'D-3', badgeColor: 'bg-red-500' },
  { label: '학사', title: '8월 졸업예정자 졸업요건 확인', badge: 'D-14', badgeColor: 'bg-amber-500' },
  { label: '취업/인턴', title: '하계 인턴십 연계 기업 모집', badge: 'D-7', badgeColor: 'bg-orange-500' },
]

export default function Home() {
  return (
    <div className="flex flex-col gap-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-500 to-violet-500 px-8 py-14 shadow-xl shadow-indigo-200/60">
        {/* Background blobs */}
        <div className="pointer-events-none absolute -right-16 -top-16 h-72 w-72 rounded-full bg-violet-400/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-12 -left-12 h-56 w-56 rounded-full bg-blue-400/20 blur-2xl" />

        <div className="relative grid grid-cols-1 items-center gap-10 md:grid-cols-2">
          {/* Text */}
          <div>
            <span className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3.5 py-1 text-xs font-medium text-indigo-100 backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
              AI 기반 맞춤 공지 알림
            </span>
            <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-white">
              학교 공지,<br />
              이제 놓치지<br />
              마세요
            </h1>
            <p className="mt-4 text-base leading-relaxed text-indigo-100">
              관심사를 등록하면 AI가 공지를 분석해<br className="hidden sm:block" />
              꼭 필요한 알림만 골라 요약해드려요
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/login"
                className="rounded-xl bg-white px-6 py-3 text-sm font-bold text-indigo-600 shadow-md shadow-indigo-900/20 transition-all hover:bg-indigo-50 hover:shadow-lg active:scale-95"
              >
                지금 시작하기 →
              </Link>
              <Link
                href="/feed"
                className="rounded-xl border border-white/25 bg-white/10 px-6 py-3 text-sm font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/20 active:scale-95"
              >
                피드 미리보기
              </Link>
            </div>
          </div>

          {/* Decorative notification cards */}
          <div className="hidden flex-col gap-3 md:flex">
            {MOCK_NOTICES.map((n, i) => (
              <div
                key={i}
                className="rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur-sm"
                style={{ opacity: 1 - i * 0.15, transform: `translateY(${i * 4}px)` }}
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="rounded-full bg-white/15 px-2.5 py-0.5 text-[11px] font-medium text-indigo-100">
                    {n.label}
                  </span>
                  <span className={`ml-auto rounded-full ${n.badgeColor} px-2 py-0.5 text-[11px] font-bold text-white`}>
                    {n.badge}
                  </span>
                </div>
                <p className="text-sm font-medium text-white">{n.title}</p>
                {i === 0 && (
                  <>
                    <p className="mt-1.5 text-xs leading-relaxed text-indigo-200">
                      직전학기 성적 3.5 이상 학생 대상. 포털에서 온라인으로 신청하세요.
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button className="rounded-full bg-white/15 px-3 py-1 text-xs font-medium text-white hover:bg-white/25">
                        👍 도움돼요
                      </button>
                      <button className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-indigo-200">
                        👎 별로예요
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section>
        <p className="mb-4 text-center text-sm font-medium text-zinc-400 uppercase tracking-widest">주요 기능</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {FEATURES.map(({ icon, title, desc, gradient, bg, border }) => (
            <div
              key={title}
              className={`relative overflow-hidden rounded-2xl border ${border} ${bg} p-6`}
            >
              <div className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${gradient} text-xl shadow-md`}>
                {icon}
              </div>
              <h3 className="mb-1.5 font-bold text-zinc-900">{title}</h3>
              <p className="text-sm leading-relaxed text-zinc-500">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Stats */}
      <section className="rounded-2xl border border-indigo-100 bg-white/60 px-8 py-6 backdrop-blur">
        <div className="grid grid-cols-3 divide-x divide-indigo-100 text-center">
          {[
            { num: 'AI 요약', sub: '핵심만 3줄로' },
            { num: '맞춤 필터', sub: '관심사 기반 선별' },
            { num: '👍 피드백', sub: '학습하는 추천' },
          ].map(({ num, sub }) => (
            <div key={num} className="px-4">
              <p className="text-base font-bold text-indigo-600">{num}</p>
              <p className="mt-0.5 text-xs text-zinc-400">{sub}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
