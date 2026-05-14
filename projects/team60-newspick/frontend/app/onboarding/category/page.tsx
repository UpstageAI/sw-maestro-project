"use client";

import Link from "next/link";
import { PhoneFrame } from "../../../components/phone-frame";
import { feedHref, type CategoryId } from "../../../lib/categories";
import { useCategoryStore } from "../../../lib/store/category";

const categories: Array<{
  id: CategoryId;
  title: string;
  description: string;
}> = [
  {
    id: "tech",
    title: "테크",
    description: "AI와 기술 흐름을 한눈에",
  },
  {
    id: "economy",
    title: "경제",
    description: "돈과 시장의 움직임을 쉽게",
  },
  {
    id: "policy",
    title: "정책",
    description: "정책 변화와 사회 방향을 이해해요",
  },
  {
    id: "issue",
    title: "이슈",
    description: "지금 사람들이 주목하는 이야기",
  },
];

function CategoryIcon({ id }: { id: CategoryId }) {
  const commonProps = {
    "aria-hidden": true,
    className: "h-[22px] w-[22px]",
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 2,
    viewBox: "0 0 24 24",
  };

  if (id === "tech") {
    return (
      <svg {...commonProps}>
        <rect x="6" y="6" width="12" height="12" rx="3" />
        <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
        <path d="M10 12h.01M12 10h.01M14 12h.01" />
      </svg>
    );
  }

  if (id === "economy") {
    return (
      <svg {...commonProps}>
        <circle cx="6.5" cy="17.5" r="3" />
        <path d="M4 13l4-4 4 3 6-7" />
        <path d="M15 5h3v3" />
      </svg>
    );
  }

  if (id === "policy") {
    return (
      <svg {...commonProps}>
        <rect x="3.25" y="3.25" width="17.5" height="17.5" rx="4" />
        <path d="M7.25 10.25h5.5" />
        <path d="M7.25 15.25l2.75 2.75 6.75-7.5" />
      </svg>
    );
  }

  return (
    <svg {...commonProps}>
      <path d="M5 6.5h11a4 4 0 0 1 4 4v1.5a4 4 0 0 1-4 4h-5l-4.5 3v-3H5a4 4 0 0 1-4-4v-1.5a4 4 0 0 1 4-4z" />
      <circle cx="18.5" cy="5.5" r="2.5" />
    </svg>
  );
}

export default function CategoryPage() {
  const selected = useCategoryStore((state) => state.selected);
  const toggle = useCategoryStore((state) => state.toggle);
  const selectedLabels = categories
    .filter((category) => selected.includes(category.id))
    .map((category) => category.title);
  const canContinue = selectedLabels.length > 0;
  const reportHref = feedHref(selected);
  const actionHelper = canContinue
    ? `${selectedLabels.join(", ")} 중심으로 준비할게요.`
    : "하나 이상 선택하면 리포트를 만들 수 있어요.";

  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-5 py-6 text-ink">
      <PhoneFrame>
        <section
          aria-label="관심 카테고리 선택"
          className="relative flex-1 px-[22px] pb-6 pt-16 text-left"
        >
          <Link
            href="/"
            aria-label="이전 화면"
            className="absolute left-[18px] top-[18px] grid h-[38px] w-[38px] place-items-center rounded-[14px] bg-transparent text-[32px] font-medium leading-none text-ink active:bg-chip"
          >
            ‹
          </Link>

          <header className="mb-[22px]">
            <p className="mb-2 text-[13px] font-extrabold text-brand-500">맞춤 설정</p>
            <h1 className="mb-2.5 text-[28px] font-extrabold leading-[1.25] text-ink break-keep">
              관심 있는 뉴스를 골라주세요
            </h1>
            <p className="text-[15px] font-medium leading-[1.55] text-muted break-keep">
              선택한 분야를 중심으로 요약, 퀴즈, 데일리 리포트를 준비할게요.
            </p>
          </header>

          <div className="grid gap-2.5" role="group" aria-label="뉴스 카테고리">
            {categories.map((category) => {
              const isSelected = selected.includes(category.id);

              return (
                <button
                  key={category.id}
                  type="button"
                  aria-label={category.title}
                  aria-pressed={isSelected}
                  onClick={() => toggle(category.id)}
                  className={`grid min-h-[76px] grid-cols-[44px_1fr_24px] items-center gap-3 rounded-[20px] border py-[14px] pl-[14px] pr-4 text-left transition-[transform,border-color,background-color] duration-150 active:scale-[0.99] ${
                    isSelected
                      ? "border-[rgba(255,138,61,0.34)] bg-brand-50"
                      : "border-transparent bg-chip"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`grid h-11 w-11 place-items-center rounded-2xl ${
                      isSelected ? "bg-brand-500 text-white" : "bg-white text-hint"
                    }`}
                  >
                    <CategoryIcon id={category.id} />
                  </span>
                  <span className="grid min-w-0 gap-1">
                    <span className="text-[17px] font-extrabold leading-[1.2] text-ink">
                      {category.title}
                    </span>
                    <span className="text-[13px] font-semibold leading-[1.35] text-muted">
                      {category.description}
                    </span>
                  </span>
                  <span
                    aria-hidden="true"
                    className={`flex h-6 w-6 items-center justify-center rounded-full text-[13px] font-black ${
                      isSelected ? "bg-brand-500 text-white" : "bg-chip text-transparent"
                    }`}
                  >
                    ✓
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <footer className="bg-surface px-[22px] pb-6">
          {canContinue ? (
            <Link
              href={reportHref}
              role="button"
              className="flex min-h-[54px] w-full items-center justify-center rounded-2xl bg-brand-500 text-[17px] font-bold text-white active:bg-brand-600"
            >
              내 리포트 만들기
            </Link>
          ) : (
            <button
              type="button"
              disabled
              className="flex min-h-[54px] w-full items-center justify-center rounded-2xl bg-[#d1d6db] text-[17px] font-bold text-white"
            >
              카테고리를 선택해 주세요
            </button>
          )}
          <p className="mt-2.5 min-h-[18px] text-center text-[13px] font-semibold leading-[1.35] text-hint">
            {actionHelper}
          </p>
        </footer>
      </PhoneFrame>
    </main>
  );
}
