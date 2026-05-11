import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { EditPetClient } from "./edit-pet-client";

type Props = { params: Promise<{ id: string }> };

export default async function EditPetPage({ params }: Props) {
  const { id } = await params;
  const supabase = await createSupabaseServerClient();
  const { data: pet, error } = await supabase
    .from("pets")
    .select("id, name, species, honorific, gender, created_at, updated_at")
    .eq("id", id)
    .single();

  if (error || !pet) {
    notFound();
  }

  return (
    <main className="flex flex-1 flex-col">
      <SiteHeader />

      {/* Hero — deep section */}
      <section className="bg-deep text-background px-6 py-20 sm:px-10 lg:py-24">
        <div className="mx-auto max-w-[1600px]">
          <div className="mb-8 flex items-center gap-3 text-sm tracking-[0.3em] text-accent uppercase">
            <span className="h-px w-8 bg-accent" />
            <span>Edit Pet</span>
          </div>
          <h1
            className="font-display text-5xl leading-[0.95] sm:text-6xl lg:text-7xl"
            style={{ letterSpacing: "-0.02em" }}
          >
            {pet.name}<br />
            <span className="text-accent">정보</span> 수정
          </h1>
        </div>
      </section>

      {/* 본문 — cream 폼 */}
      <section className="bg-background text-foreground px-6 py-16 sm:px-10 lg:py-20 flex-1">
        <div className="mx-auto w-full max-w-xl">
          <EditPetClient pet={pet} />
        </div>
      </section>
    </main>
  );
}
