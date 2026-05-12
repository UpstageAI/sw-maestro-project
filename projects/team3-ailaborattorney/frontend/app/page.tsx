import Link from "next/link";

const steps = [
  {
    n: "01",
    title: "계약서 업로드",
    desc: "PDF 또는 이미지로 계약서를 올려주세요. 30초면 충분해요.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
    ),
  },
  {
    n: "02",
    title: "AI가 즉시 분석",
    desc: "근로기준법 위반 가능성, 위험도, 추천 조치를 자동으로 검토합니다.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </svg>
    ),
  },
  {
    n: "03",
    title: "결과 확인 + 질문",
    desc: "위반 항목과 근거 조항을 확인하고, 궁금한 점은 AI에게 바로 물어보세요.",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8z" />
      </svg>
    ),
  },
];

const chips = ["PDF · 이미지 지원", "약 30초 소요", "무료"];

export default function Home() {
  return (
    <section className="space-y-10">
      <div className="space-y-5 pt-4 sm:pt-8">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-toss-blue-bg px-3 py-1 text-[12px] font-semibold text-toss-blue">
          <span className="h-1.5 w-1.5 rounded-full bg-toss-blue" />
          AI 근로계약서 분석
        </span>
        <h1 className="text-[28px] sm:text-[36px] font-bold leading-[1.25] tracking-tight text-grey-900">
          근로계약서, <br className="sm:hidden" />
          <span className="text-toss-blue">AI가 5초 만에</span> 검토해드릴게요.
        </h1>
        <p className="text-[16px] sm:text-[17px] leading-relaxed text-grey-600 max-w-xl">
          최저임금, 주휴수당, 근로시간, 휴게시간까지. 사진 한 장이면 권리를 놓치지 않게 도와드릴게요.
        </p>
      </div>

      <Link
        href="/upload"
        className="group flex items-center justify-between rounded-2xl bg-toss-blue px-6 py-5 text-white shadow-[0_8px_24px_rgba(49,130,246,0.25)] hover:bg-toss-blue-hover active:bg-toss-blue-pressed transition-colors"
      >
        <span className="text-[17px] font-semibold tracking-tight">지금 분석 시작하기</span>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-hover:translate-x-0.5" aria-hidden="true">
          <path d="M9 18l6-6-6-6" />
        </svg>
      </Link>

      <div className="flex flex-wrap gap-2">
        {chips.map((c) => (
          <span key={c} className="inline-flex items-center rounded-full border border-grey-200 bg-white px-3 py-1 text-[12px] font-medium text-grey-600">
            {c}
          </span>
        ))}
      </div>

      <div className="space-y-3">
        <h2 className="text-[20px] font-bold tracking-tight text-grey-900">3단계로 끝나요</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {steps.map((s) => (
            <div
              key={s.n}
              className="rounded-2xl bg-white border border-grey-200 p-5 hover:border-grey-300 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-toss-blue-bg text-toss-blue">
                  {s.icon}
                </span>
                <span className="text-[12px] font-bold tracking-wider text-grey-400">{s.n}</span>
              </div>
              <p className="mt-4 text-[15px] font-bold text-grey-900">{s.title}</p>
              <p className="mt-1 text-[13px] leading-5 text-grey-600">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
