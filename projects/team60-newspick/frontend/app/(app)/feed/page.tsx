"use client";

import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, type MouseEvent } from "react";
import { BottomNav } from "../../../components/bottom-nav";
import { FeedLoadingProgress } from "../../../components/feed-loading-progress";
import { NewsCard } from "../../../components/news-card";
import { PhoneFrame } from "../../../components/phone-frame";
import { apiUrl } from "../../../lib/api/base";
import { fetchFeed, type ArticleSummary } from "../../../lib/api/feed";
import {
  CATEGORY_IDS,
  categoryBadgeClass,
  categoryLabel,
  categoryQuery,
  parseCategoryQuery,
  type CategoryId,
} from "../../../lib/categories";
import { subscribeSse } from "../../../lib/sse";
import { useCategoryStore } from "../../../lib/store/category";
import { isRefreshStepName, useRefreshStore, type RefreshStepName } from "../../../lib/store/refresh";

type RefreshEventData = {
  code?: string;
  message?: string;
  stage?: string;
  step?: string;
  current?: number;
  total?: number;
  count?: number;
  articleIds?: string[];
};

type ActiveRefresh = {
  close: () => void;
  runId: string;
};

const START_OVER_CONFIRM =
  "처음으로 돌아가면 진행 중인 기사 수집과 AI 요약을 취소합니다. 계속할까요?";
const DEFAULT_REFRESH_ERROR_MESSAGE = "뉴스를 다시 수집하지 못했어요. 잠시 후 다시 시도해주세요.";
const MISSING_ENVIRONMENT_ERROR_MESSAGE = "AI 설정을 읽지 못해 재수집을 완료하지 못했어요.";

function createRunId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function refreshStreamUrl(categories: readonly CategoryId[], runId: string, reset: boolean) {
  const url = new URL(apiUrl("/api/refresh-stream"));
  url.searchParams.set("runId", runId);
  if (categories.length > 0) {
    url.searchParams.set("categories", categoryQuery(categories));
  }
  if (reset) {
    url.searchParams.set("reset", "1");
  }

  return url.toString();
}

function resetFeedHref(categories: readonly CategoryId[]) {
  const params = new URLSearchParams({
    refresh: "1",
    reset: "1",
  });
  if (categories.length > 0) {
    params.set("categories", categoryQuery(categories));
  }

  return `/feed?${params.toString()}`;
}

function feedFilterHref(categories: readonly CategoryId[]) {
  const params = new URLSearchParams();
  if (categories.length > 0) {
    params.set("categories", categoryQuery(categories));
  }

  const query = params.toString();
  return query ? `/feed?${query}` : "/feed";
}

function nextFilterCategories(
  selectedCategories: readonly CategoryId[],
  category: CategoryId,
) {
  const selected = new Set(selectedCategories);

  if (selected.has(category)) {
    if (selected.size === 1) {
      return [...selectedCategories];
    }
    selected.delete(category);
  } else {
    selected.add(category);
  }

  return CATEGORY_IDS.filter((candidate) => selected.has(candidate));
}

function cancelRefreshRun(runId: string) {
  if (typeof fetch === "undefined") {
    return;
  }

  void fetch(apiUrl(`/api/refresh-stream/${encodeURIComponent(runId)}/cancel`), {
    method: "POST",
    keepalive: true,
  }).catch(() => undefined);
}

function refreshErrorMessage(message: string | undefined) {
  const trimmed = message?.trim();
  if (!trimmed) {
    return DEFAULT_REFRESH_ERROR_MESSAGE;
  }
  if (trimmed === "timeout") {
    return DEFAULT_REFRESH_ERROR_MESSAGE;
  }
  if (
    trimmed.includes("UPSTAGE_API_KEY") ||
    trimmed.includes("DATABASE_URL") ||
    trimmed.includes("AI 설정")
  ) {
    return MISSING_ENVIRONMENT_ERROR_MESSAGE;
  }
  return trimmed;
}

function removeRefreshQuery() {
  if (typeof window === "undefined") {
    return;
  }

  const url = new URL(window.location.href);
  url.searchParams.delete("refresh");
  url.searchParams.delete("reset");
  window.history.replaceState(null, "", `${url.pathname}${url.search}`);
}

function sameCategories(a: readonly CategoryId[], b: readonly CategoryId[]) {
  return a.length === b.length && a.every((category, index) => category === b[index]);
}

function isFinalizingStep(step: RefreshStepName) {
  return step === "prepare";
}

function legacyStageStep(stage: string | undefined): RefreshStepName | null {
  if (stage === "collect") {
    return "collect";
  }
  if (stage === "summarize") {
    return "summarize";
  }
  return null;
}

const PREPARE_STEPS = ["save", "embed", "quiz", "report"] as const;
const prepareStepSet = new Set<string>(PREPARE_STEPS);
const CATEGORY_FILTERS = CATEGORY_IDS.map((category) => ({
  id: category,
  label: categoryLabel(category),
}));

function prepareProgress(step: string, current: number, total: number) {
  const index = PREPARE_STEPS.findIndex((name) => name === step);
  const stepFinished = total > 0 && current >= total;
  return {
    current: index + (stepFinished ? 1 : 0),
    total: PREPARE_STEPS.length,
  };
}

function FeedQuerySkeleton() {
  return (
    <div className="mt-6 grid gap-2.5" role="status" aria-label="뉴스 불러오는 중">
      <div className="grid gap-2.5 overflow-hidden rounded-[22px] bg-chip p-4">
        <span className="skeleton-shimmer h-2.5 w-[72px] rounded-full" />
        <strong className="skeleton-shimmer h-4 w-[86%] rounded-full" />
        <p className="skeleton-shimmer h-3 w-[62%] rounded-full" />
      </div>
      <div className="grid gap-2.5 overflow-hidden rounded-[22px] bg-chip p-4">
        <span className="skeleton-shimmer h-2.5 w-[72px] rounded-full" />
        <strong className="skeleton-shimmer h-4 w-[78%] rounded-full" />
        <p className="skeleton-shimmer h-3 w-[68%] rounded-full" />
      </div>
    </div>
  );
}

function FeedEmpty() {
  return (
    <section className="flex min-h-[220px] items-center justify-center px-3 text-center">
      <p className="text-[15px] font-[800] leading-[1.5] text-muted break-keep">
        아직 보여줄 뉴스가 없어요
      </p>
    </section>
  );
}

function FeedError({ message }: { message?: string | null }) {
  const copy =
    message && message !== DEFAULT_REFRESH_ERROR_MESSAGE
      ? message
      : "뉴스를 불러오지 못했어요";

  return (
    <section className="flex min-h-[220px] items-center justify-center px-3 text-center">
      <p className="text-[15px] font-[800] leading-[1.5] text-muted break-keep">
        {copy}
      </p>
    </section>
  );
}

function ArticleList({
  articles,
  isRefetching = false,
}: {
  articles: ArticleSummary[];
  isRefetching?: boolean;
}) {
  return (
    <div
      aria-busy={isRefetching ? "true" : undefined}
      className={`feed-list-enter grid gap-3 transition-opacity duration-200 ease-out ${
        isRefetching ? "opacity-70" : "opacity-100"
      }`}
    >
      {articles.map((article) => (
        <NewsCard key={article.id} article={article} />
      ))}
    </div>
  );
}

export default function FeedPage() {
  return (
    <Suspense fallback={<FeedLoadingShell />}>
      <FeedPageContent />
    </Suspense>
  );
}

function FeedLoadingShell() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-5 py-6 text-ink">
      <PhoneFrame>
        <div className="page-enter-soft min-h-0 flex-1 overflow-y-auto px-[22px] pb-[18px] pt-[18px]">
          <FeedQuerySkeleton />
        </div>
        <BottomNav active="home" />
      </PhoneFrame>
    </main>
  );
}

function FeedPageContent() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const storedCategories = useCategoryStore((state) => state.selected);
  const setStoredCategories = useCategoryStore((state) => state.setSelected);
  const refreshError = useRefreshStore((state) => state.errorMessage);
  const refreshStatus = useRefreshStore((state) => state.status);
  const activeRefreshKey = useRef<string | null>(null);
  const activeRefresh = useRef<ActiveRefresh | null>(null);
  const resolvedSearchParams =
    searchParams ?? new URLSearchParams(typeof window === "undefined" ? "" : window.location.search);
  const categoryParam = resolvedSearchParams.get("categories");
  const shouldRefresh = resolvedSearchParams.get("refresh") === "1";
  const shouldReset = resolvedSearchParams.get("reset") === "1";
  const selectedCategories = useMemo(() => {
    const categories = parseCategoryQuery(categoryParam);
    return categories.length > 0 ? categories : storedCategories;
  }, [categoryParam, storedCategories]);
  const selectedCategoryQuery = useMemo(
    () => categoryQuery(selectedCategories),
    [selectedCategories],
  );
  const selectedCategorySet = useMemo(() => new Set(selectedCategories), [selectedCategories]);
  const refreshRequestKey = `${selectedCategoryQuery}:${resolvedSearchParams.toString()}`;

  const { data, error, isFetching, isLoading } = useQuery({
    queryKey: ["feed", selectedCategoryQuery],
    queryFn: () => fetchFeed(selectedCategories),
    placeholderData: keepPreviousData,
  });

  const articles = data?.articles ?? [];
  const hasArticles = articles.length > 0;
  const showRefreshLoading =
    refreshStatus === "loading" || (shouldRefresh && refreshStatus === "idle");
  const showQueryLoading = isLoading && !showRefreshLoading;
  const hasBlockingError = Boolean(error) || (refreshStatus === "error" && (Boolean(refreshError) || !hasArticles));
  const isFeedRefetching = isFetching && hasArticles && !showRefreshLoading;
  const articleListKey = articles.map((article) => article.id).join("|");

  useEffect(() => {
    if (selectedCategories.length > 0 && !sameCategories(selectedCategories, storedCategories)) {
      setStoredCategories(selectedCategories);
    }
  }, [selectedCategories, setStoredCategories, storedCategories]);

  useEffect(() => {
    if (!shouldRefresh) {
      return;
    }
    if (activeRefreshKey.current === refreshRequestKey) {
      return;
    }

    const runId = createRunId();
    activeRefreshKey.current = refreshRequestKey;

    const { reset, setErrorMessage, setFinalizing, setStatus, setStep } =
      useRefreshStore.getState();
    const active: ActiveRefresh = {
      close: () => undefined,
      runId,
    };
    activeRefresh.current = active;

    const finishRefresh = (status: "done" | "error") => {
      activeRefreshKey.current = null;
      if (activeRefresh.current?.runId === runId) {
        activeRefresh.current = null;
      }
      setFinalizing(false);
      if (status === "done") {
        setErrorMessage(null);
      }
      setStatus(status);
      removeRefreshQuery();
    };

    const failRefresh = (message?: string) => {
      setErrorMessage(refreshErrorMessage(message));
      finishRefresh("error");
      void queryClient.invalidateQueries({ queryKey: ["feed"] });
    };

    reset();
    setStatus("loading");

    if (typeof EventSource === "undefined") {
      failRefresh();
      return;
    }

    const streamUrl = refreshStreamUrl(selectedCategories, runId, shouldReset);
    const close = subscribeSse<RefreshEventData>(streamUrl, {
      onEvent: (event, data) => {
        if (event === "error") {
          failRefresh(data.message);
          return;
        }

        if (event !== "step" && event !== "progress") {
          return;
        }

        const rawStep = data.step;
        const step = isRefreshStepName(rawStep)
          ? rawStep
          : legacyStageStep(data.stage);

        if (
          rawStep &&
          prepareStepSet.has(rawStep) &&
          typeof data.current === "number" &&
          typeof data.total === "number"
        ) {
          const progress = prepareProgress(rawStep, data.current, data.total);
          setStep("prepare", progress.current, progress.total);
          setFinalizing(true);
          return;
        }

        if (
          rawStep === "extract" &&
          typeof data.current === "number" &&
          typeof data.total === "number" &&
          data.current > 0 &&
          data.current <= data.total
        ) {
          setStep("summarize", 0, data.current);
          setFinalizing(false);
          return;
        }

        if (
          step &&
          typeof data.current === "number" &&
          typeof data.total === "number"
        ) {
          setStep(step, data.current, data.total);
          setFinalizing(
            isFinalizingStep(step) ||
              (step === "summarize" && data.total > 0 && data.current >= data.total),
          );
          if (step === "summarize" && data.total > 0 && data.current >= data.total) {
            setStep("prepare", 0, PREPARE_STEPS.length);
          }
          return;
        }

        if (!step) {
          return;
        }

        if (step === "collect") {
          const count = data.count ?? data.articleIds?.length ?? 0;
          setStep("collect", count, count);
          setFinalizing(false);
          return;
        }

        if (step === "summarize") {
          const count = data.count ?? data.articleIds?.length ?? 0;
          setStep("summarize", count, count);
          setFinalizing(count > 0);
        }
      },
      onDone: () => {
        setFinalizing(true);
        setStep("prepare", PREPARE_STEPS.length, PREPARE_STEPS.length);
        removeRefreshQuery();
        void queryClient.cancelQueries({ queryKey: ["feed", selectedCategoryQuery] });
        void fetchFeed(selectedCategories)
          .then((feed) => {
            queryClient.setQueryData(["feed", selectedCategoryQuery], feed);
            finishRefresh("done");
          })
          .catch(() => {
            setErrorMessage(DEFAULT_REFRESH_ERROR_MESSAGE);
            finishRefresh("error");
          });
      },
      onError: () => {
        failRefresh();
      },
    });

    active.close = close;

    return () => {
      close();
      if (activeRefreshKey.current === refreshRequestKey) {
        activeRefreshKey.current = null;
      }
      if (activeRefresh.current?.runId === runId) {
        activeRefresh.current = null;
      }
    };
  }, [queryClient, refreshRequestKey, selectedCategories, selectedCategoryQuery, shouldRefresh, shouldReset]);

  const handleStartOver = (event: MouseEvent<HTMLAnchorElement>) => {
    if (refreshStatus === "loading" && activeRefresh.current) {
      if (!window.confirm(START_OVER_CONFIRM)) {
        event.preventDefault();
        return;
      }

      const active = activeRefresh.current;
      active.close();
      cancelRefreshRun(active.runId);
      activeRefresh.current = null;
      activeRefreshKey.current = null;
      useRefreshStore.getState().reset();
      window.history.pushState({}, "", "/");
    }
  };

  const handleResetRefresh = () => {
    const { reset, setStatus } = useRefreshStore.getState();
    reset();
    setStatus("loading");
  };

  const handleCategoryFilterClick = useCallback(
    (category: CategoryId) => {
      const nextCategories = nextFilterCategories(selectedCategories, category);
      if (sameCategories(nextCategories, selectedCategories)) {
        return;
      }

      if (typeof window !== "undefined") {
        window.history.pushState({}, "", feedFilterHref(nextCategories));
      }
      setStoredCategories(nextCategories);
    },
    [selectedCategories, setStoredCategories],
  );

  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-5 py-6 text-ink">
      <PhoneFrame>
        <div className="page-enter-soft min-h-0 flex-1 overflow-y-auto px-[22px] pb-[18px] pt-[18px]">
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-[13px] font-[800] text-brand-500">Home</p>
            <div className="flex items-center gap-1.5">
              <Link
                href={resetFeedHref(selectedCategories)}
                onClick={handleResetRefresh}
                className="rounded-full bg-brand-50 px-3 py-1.5 text-[12px] font-[850] text-brand-500 no-underline active:bg-line"
              >
                다시 수집
              </Link>
              <Link
                href="/"
                onClick={handleStartOver}
                className="rounded-full bg-chip px-3 py-1.5 text-[12px] font-[800] text-hint no-underline active:bg-line"
              >
                처음으로
              </Link>
            </div>
          </div>
          <h1 className="mb-2.5 text-[30px] font-[850] leading-[1.22] text-ink">
            오늘의 뉴스
          </h1>
          <p className="max-w-[280px] text-[15px] font-[550] leading-[1.55] text-muted break-keep">
            AI가 관심 분야의 주요 뉴스를 정리하고 있어요.
          </p>
          <div aria-label="카테고리 필터" role="group" className="mt-3 flex flex-wrap gap-1.5">
            {CATEGORY_FILTERS.map(({ id, label }) => {
              const isSelected = selectedCategorySet.has(id);

              return (
                <button
                  key={id}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => handleCategoryFilterClick(id)}
                  className={`inline-flex min-h-7 items-center rounded-full px-2.5 text-[12px] font-[850] transition-[background-color,color,transform] active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${
                    isSelected ? categoryBadgeClass(label) : "bg-chip text-hint"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {showRefreshLoading ? <FeedLoadingProgress /> : null}
          {showQueryLoading ? <FeedQuerySkeleton /> : null}
          {!showRefreshLoading && !showQueryLoading ? (
            <div className="mt-6">
              {hasBlockingError ? <FeedError message={refreshError} /> : null}
              {!hasBlockingError && !hasArticles ? <FeedEmpty /> : null}
              {!hasBlockingError && hasArticles ? (
                <ArticleList
                  key={articleListKey}
                  articles={articles}
                  isRefetching={isFeedRefetching}
                />
              ) : null}
            </div>
          ) : null}
        </div>

        <BottomNav active="home" />
      </PhoneFrame>
    </main>
  );
}
