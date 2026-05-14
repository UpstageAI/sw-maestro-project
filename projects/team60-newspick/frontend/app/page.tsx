import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-5 py-6 text-ink">
      <section className="relative flex h-[min(820px,calc(100dvh-40px))] w-full max-w-[390px] flex-col overflow-hidden rounded-phone bg-surface shadow-[0_18px_50px_rgba(25,31,40,0.12)]">
        <div className="flex items-center justify-between px-6 py-4 text-[13px] font-bold text-ink">
          <span>9:41</span>
          <span>5G 100%</span>
        </div>

        <div className="flex flex-1 flex-col items-center justify-center px-7 text-center">
          <Image
            src="/newspick.png"
            alt="NewPick logo"
            width={76}
            height={76}
            priority
            className="mb-6 rounded-3xl shadow-[0_16px_32px_rgba(255,138,61,0.24)]"
          />
          <h1 className="text-[42px] font-extrabold leading-[1.12] text-ink">NewPick</h1>
          <p className="mt-4 max-w-[280px] text-[17px] font-medium leading-[1.55] text-muted break-keep">
            AI가 오늘의 뉴스를 골라 짧게 요약하고 퀴즈로 정리해요.
          </p>
        </div>

        <div className="px-7 pb-10">
          <Link
            href="/onboarding/category"
            role="button"
            className="flex h-[54px] w-full items-center justify-center rounded-2xl bg-brand-500 text-[17px] font-bold text-white shadow-[0_12px_24px_rgba(255,138,61,0.22)] transition-colors active:bg-brand-600"
          >
            서비스 시작하기
          </Link>
        </div>
      </section>
    </main>
  );
}
