import { redirect } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { getCurrentUser } from "@/lib/server/auth";
import { NewPetClient } from "./new-pet-client";

export default async function NewPetPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />

      {/* Hero — deep section */}
      <section className="bg-deep text-background px-6 py-20 sm:px-10 lg:py-24">
        <div className="mx-auto max-w-[1600px]">
          <div className="mb-8 flex items-center gap-3 text-sm tracking-[0.3em] text-accent uppercase">
            <span className="h-px w-8 bg-accent" />
            <span>New Pet · Welcome</span>
          </div>
          <h1
            className="font-display text-5xl leading-[0.95] sm:text-6xl lg:text-7xl"
            style={{ letterSpacing: "-0.02em" }}
          >
            새 가족을<br />
            <span className="text-accent">등록</span>해주세요
          </h1>
          <p className="mt-8 text-lg leading-relaxed text-background/70 sm:mt-10 sm:text-xl">
            이름과 종, 호칭을 알려주세요.<br />
            호칭은 일기에서 반려동물이 당신을 부르는 말이에요.
          </p>
        </div>
      </section>

      {/* 본문 — cream 폼 */}
      <section className="bg-background text-foreground px-6 py-16 sm:px-10 lg:py-20 flex-1">
        <div className="mx-auto w-full max-w-xl">
          <NewPetClient />
        </div>
      </section>
    </main>
  );
}
