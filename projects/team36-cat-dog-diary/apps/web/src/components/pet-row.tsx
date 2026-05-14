import Link from "next/link";
import type { Icon } from "@phosphor-icons/react";
import {
  Cat,
  Dog,
  GenderFemale,
  GenderMale,
  PawPrint,
  Plus,
} from "@phosphor-icons/react/dist/ssr";
import type { Diary, Pet } from "@cat-dog-diary/shared-types";
import { cn } from "@/lib/utils";
import { type SpeciesKind, normalizeSpecies } from "@/lib/species";
import { DiaryCard } from "@/components/diary-card";
import { PetRowMenu } from "@/components/pet-row-menu";

interface PetRowProps {
  pet: Pet;
  diaries: Diary[];
  newRemaining: number;
  /** 1-base. "PET 0N" stamp에 사용. */
  index: number;
  /** 색블록 교차용 — light(cream)·deep(dark brown). */
  variant: "light" | "deep";
}

const SPECIES_ICON: Record<SpeciesKind, Icon> = {
  cat: Cat,
  dog: Dog,
  other: PawPrint,
};

const GENDER_ICON: Record<Pet["gender"], Icon | null> = {
  male: GenderMale,
  female: GenderFemale,
  unknown: null,
};

function daysTogether(createdAt: string): number {
  const ms = Date.now() - new Date(createdAt).getTime();
  return Math.max(1, Math.floor(ms / (1000 * 60 * 60 * 24)) + 1);
}

export function PetRow({
  pet,
  diaries,
  newRemaining,
  index,
  variant,
}: PetRowProps) {
  const SpeciesIcon = SPECIES_ICON[normalizeSpecies(pet.species)];
  const GenderIcon = GENDER_ICON[pet.gender];
  const canCreate = newRemaining > 0;
  const estYear = new Date(pet.created_at).getFullYear();
  const days = daysTogether(pet.created_at);
  const diaryCount = diaries.length;
  const indexLabel = `Pet ${String(index).padStart(2, "0")}`;
  const isDeep = variant === "deep";

  return (
    <section className="w-full">
      <header
        className={cn(
          "flex items-end justify-between border-b pb-8 mb-10 gap-4",
          isDeep ? "border-deep-border" : "border-border",
        )}
      >
        <div className="min-w-0">
          <div
            className={cn(
              "flex items-center gap-3 text-xs tracking-[0.3em] uppercase mb-4",
              isDeep ? "text-accent" : "text-muted-foreground",
            )}
          >
            <span>— {indexLabel}</span>
            <span
              className={cn(
                "px-3 py-1 rounded-full border text-xs",
                isDeep
                  ? "border-deep-border bg-deep"
                  : "border-border bg-card",
              )}
            >
              Est. {estYear}
            </span>
          </div>
          <h2
            className="font-display text-5xl sm:text-6xl lg:text-7xl flex items-center gap-4 tracking-tight"
            style={{ letterSpacing: "-0.02em" }}
          >
            <span className="truncate">{pet.name}</span>
            <SpeciesIcon
              size={48}
              weight="duotone"
              className={cn(
                "shrink-0",
                isDeep ? "text-accent" : "text-primary",
              )}
              aria-hidden
            />
          </h2>
          <div
            className={cn(
              "mt-4 flex items-center gap-2 text-base",
              isDeep ? "text-background/70" : "text-muted-foreground",
            )}
          >
            <span>호칭</span>
            <span
              className={cn(
                "font-medium",
                isDeep ? "text-background" : "text-foreground",
              )}
            >
              {pet.honorific}
            </span>
            {GenderIcon ? (
              <>
                <span aria-hidden>·</span>
                <GenderIcon size={14} weight="bold" aria-hidden />
              </>
            ) : null}
            <span aria-hidden>·</span>
            <span>{pet.species}</span>
          </div>
        </div>

        <div className="flex items-start gap-10 sm:gap-16">
          <div className="text-right">
            <div className="font-display text-4xl sm:text-5xl lg:text-6xl">
              {diaryCount}
            </div>
            <div
              className={cn(
                "text-sm mt-2",
                isDeep ? "text-background/60" : "text-muted-foreground",
              )}
            >
              일기
            </div>
          </div>
          <div className="text-right">
            <div className="font-display text-4xl sm:text-5xl lg:text-6xl">
              {days.toLocaleString("ko-KR")}
            </div>
            <div
              className={cn(
                "text-sm mt-2",
                isDeep ? "text-background/60" : "text-muted-foreground",
              )}
            >
              함께한 날
            </div>
          </div>
          <PetRowMenu petId={pet.id} petName={pet.name} />
        </div>
      </header>

      {/* 카드 fixed width(w-72) + 가로 스크롤 — 일기 늘어나면 우측으로 스크롤
          (ADR-0013 §메인 본문: 펫별 row × 가로 캐러셀). */}
      <div className="-mx-6 flex gap-4 overflow-x-auto px-6 pb-2 sm:-mx-10 sm:px-10 [scrollbar-width:thin]">
        <NewDiaryCard
          petId={pet.id}
          disabled={!canCreate}
          variant={variant}
        />
        {diaries.map((d) => (
          <DiaryCard key={d.id} diary={d} />
        ))}
      </div>
    </section>
  );
}

function NewDiaryCard({
  petId,
  disabled,
  variant,
}: {
  petId: string;
  disabled: boolean;
  variant: "light" | "deep";
}) {
  const isDeep = variant === "deep";
  const baseClass =
    "group/new-diary flex aspect-[3/4] w-72 shrink-0 flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed text-sm font-medium transition-all";

  if (disabled) {
    return (
      <div
        className={cn(
          baseClass,
          isDeep
            ? "border-deep-border text-background/30"
            : "border-border text-muted-foreground/40",
          "cursor-not-allowed",
        )}
        aria-disabled
        title="오늘 새 일기 한도(5회)를 모두 썼어요. 자정에 초기화돼요."
      >
        <Plus size={48} weight="light" aria-hidden />
        <span>오늘 한도 끝</span>
      </div>
    );
  }

  return (
    <Link
      href={{ pathname: "/diaries/new", query: { pet_id: petId } }}
      className={cn(
        baseClass,
        isDeep
          ? "border-deep-border text-background/70 hover:border-accent hover:bg-deep/40 hover:text-accent"
          : "border-border bg-card/40 text-muted-foreground hover:border-primary hover:bg-card hover:text-primary",
      )}
    >
      <Plus
        size={48}
        weight="light"
        aria-hidden
        className="transition-transform group-hover/new-diary:scale-110"
      />
      <span className="tracking-wide">새 일기</span>
    </Link>
  );
}
