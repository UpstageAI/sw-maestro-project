import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export function EmptyStateCard() {
  return (
    <section className="bg-deep text-background py-32 px-6 sm:px-10">
      <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
        <div className="mb-6 flex items-center gap-3 text-xs tracking-[0.3em] uppercase text-accent">
          <span className="h-px w-8 bg-accent" />
          <span>Welcome — Start Here</span>
          <span className="h-px w-8 bg-accent" />
        </div>
        <h1
          className="font-display text-5xl leading-tight sm:text-6xl"
          style={{ letterSpacing: "-0.02em" }}
        >
          첫 반려동물을<br />
          <span className="text-accent">등록</span>해주세요
        </h1>
        <p className="mt-6 text-base leading-relaxed text-background/70 sm:text-lg">
          이름·종·호칭만 알려주면 일기 시작 준비 끝.<br />
          사진 한 장과 키워드 한 줄로 1인칭 일기가 자동 생성돼요.
        </p>
        <Link
          href="/pets/new"
          className={buttonVariants({
            size: "lg",
            className:
              "mt-10 bg-accent text-foreground hover:bg-accent/80 px-8 h-12 rounded-md text-base font-medium",
          })}
        >
          + 새 펫 추가하기
        </Link>
      </div>
    </section>
  );
}
