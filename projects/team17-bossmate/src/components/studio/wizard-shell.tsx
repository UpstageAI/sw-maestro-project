"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, ArrowRight, ImagePlus, ClipboardList } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { StepProgress, type StepDef } from "./step-progress";
import { StoreForm } from "./store-form";
import { ProcessingStep } from "./processing-step";
import { ResultStep } from "./result-step";
import type {
  AgentTrace,
  GeneratedContent,
  JobRecord,
  PromotionRequest,
} from "@/lib/types";

const STEPS: StepDef[] = [
  { key: "info", label: "가게 정보", short: "정보" },
  { key: "processing", label: "AI 작업", short: "작업" },
  { key: "result", label: "결과 확인", short: "결과" },
];

const DEFAULT_REQUEST: PromotionRequest = {
  store: {
    storeName: "",
    category: "",
    vibe: "따뜻한",
    description: "",
  },
  purpose: "new-menu",
  detail: "",
  platform: "instagram",
  feedback: "",
};

const POLL_INTERVAL_MS = 5000;
const POLL_MAX_MS = 5 * 60 * 1000;

export function WizardShell() {
  const [stepIdx, setStepIdx] = useState(0);
  const [request, setRequest] = useState<PromotionRequest>(DEFAULT_REQUEST);
  const [result, setResult] = useState<GeneratedContent | null>(null);
  const [busy, setBusy] = useState(false);
  const [processingStartedAt, setProcessingStartedAt] = useState(0);
  const [agentTrace, setAgentTrace] = useState<AgentTrace[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelledRef = useRef(false);

  const canNext = useMemo(() => {
    if (stepIdx === 0) {
      return (
        request.store.storeName.trim().length > 0 &&
        request.store.category.trim().length > 0 &&
        request.store.vibe.trim().length > 0 &&
        request.detail.trim().length > 0
      );
    }
    return true;
  }, [stepIdx, request]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const pollJob = useCallback(
    (jobId: string, startedAt: number) => {
      const startTime = Date.now();

      const tick = async () => {
        if (cancelledRef.current) return;
        if (Date.now() - startTime > POLL_MAX_MS) {
          toast.error("응답이 너무 오래 걸려요. 잠시 후 다시 시도해주세요.");
          setBusy(false);
          setStepIdx(0);
          return;
        }
        try {
          const res = await fetch(`/api/cards/${jobId}`, { cache: "no-store" });
          if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data?.error || `조회 실패 (HTTP ${res.status})`);
          }
          const job = (await res.json()) as JobRecord;
          setAgentTrace(job.agentTrace ?? []);

          if (job.status === "done" && job.result) {
            stopPolling();
            setResult(job.result);
            setBusy(false);
            setStepIdx(2);
            return;
          }
          if (job.status === "error") {
            stopPolling();
            toast.error(job.error || "생성 중 오류가 발생했어요.");
            setBusy(false);
            setStepIdx(0);
            return;
          }
          pollTimerRef.current = setTimeout(tick, POLL_INTERVAL_MS);
        } catch (err) {
          stopPolling();
          toast.error(err instanceof Error ? err.message : "조회 오류");
          setBusy(false);
          setStepIdx(0);
        }
      };

      pollTimerRef.current = setTimeout(tick, POLL_INTERVAL_MS);
      void startedAt;
    },
    [stopPolling],
  );

  const startGenerate = useCallback(
    async (overrideRequest?: PromotionRequest) => {
      stopPolling();
      cancelledRef.current = false;
      setBusy(true);
      setAgentTrace([]);
      setProcessingStartedAt(Date.now());
      setStepIdx(1);

      const payload = overrideRequest ?? request;
      try {
        const res = await fetch("/api/cards/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok || !data?.id) {
          const message = data?.error || `생성 실패 (HTTP ${res.status})`;
          toast.error(message);
          setBusy(false);
          setStepIdx(0);
          return;
        }
        setActiveJobId(data.id as string);
        pollJob(data.id as string, Date.now());
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "네트워크 오류");
        setBusy(false);
        setStepIdx(0);
      }
    },
    [request, pollJob, stopPolling],
  );

  const startRetry = useCallback(
    async (feedback?: string) => {
      if (!activeJobId) {
        startGenerate();
        return;
      }
      stopPolling();
      cancelledRef.current = false;
      setBusy(true);
      setAgentTrace([]);
      setProcessingStartedAt(Date.now());
      setStepIdx(1);

      try {
        const res = await fetch(`/api/cards/${activeJobId}/retry`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ feedback: feedback ?? "" }),
        });
        const data = await res.json();
        if (!res.ok || !data?.id) {
          throw new Error(data?.error || `재생성 실패 (HTTP ${res.status})`);
        }
        setActiveJobId(data.id as string);
        pollJob(data.id as string, Date.now());
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "재생성 오류");
        setBusy(false);
        setStepIdx(2);
      }
    },
    [activeJobId, pollJob, startGenerate, stopPolling],
  );

  const handleNext = () => {
    if (!canNext) return;
    if (stepIdx === 0) {
      startGenerate();
      return;
    }
    setStepIdx((i) => Math.min(STEPS.length - 1, i + 1));
  };

  const handleEdit = () => {
    cancelledRef.current = true;
    stopPolling();
    setStepIdx(0);
  };
  const handleRestart = () => {
    cancelledRef.current = true;
    stopPolling();
    setRequest(DEFAULT_REQUEST);
    setResult(null);
    setActiveJobId(null);
    setAgentTrace([]);
    setStepIdx(0);
  };

  return (
    <div className="flex flex-col">
      <StepProgress steps={STEPS} current={stepIdx} />

      <div className="relative">
        <AnimatePresence mode="wait">
          {stepIdx === 0 && (
            <StepFrame key="info">
              <StepHeader
                icon={ClipboardList}
                eyebrow="STEP 1"
                title="가게 정보를 알려주세요"
                subtitle="가게 이름, 업종, 분위기, 홍보 상세 내용을 입력하면 카드 한 장과 SNS 캡션을 만들어 드려요."
              />
              <StoreForm value={request} onChange={setRequest} />
              <Footer
                onPrev={undefined}
                onNext={handleNext}
                disabledNext={!canNext}
                nextLabel="다음 — 홍보물 만들기"
                hint={!canNext ? "가게명, 업종, 분위기, 홍보 상세 내용을 입력해 주세요" : undefined}
              />
            </StepFrame>
          )}

          {stepIdx === 1 && (
            <StepFrame key="processing" wide>
              <ProcessingStep
                startedAt={processingStartedAt}
                agentTrace={agentTrace}
              />
            </StepFrame>
          )}

          {stepIdx === 2 && result && (
            <StepFrame key="result" wide>
              <ResultStep
                result={result}
                busy={busy}
                onRegenerate={(fb) => startRetry(fb)}
                onEdit={handleEdit}
                onRestart={handleRestart}
              />
            </StepFrame>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

interface StepFrameProps {
  children: React.ReactNode;
  wide?: boolean;
}

function StepFrame({ children, wide = false }: StepFrameProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.32, ease: "easeOut" }}
      className={
        "mx-auto flex w-full flex-col gap-8 px-5 py-8 sm:py-12 " +
        (wide ? "max-w-5xl" : "max-w-2xl")
      }
    >
      {children}
    </motion.section>
  );
}

function StepHeader({
  icon: Icon,
  eyebrow,
  title,
  subtitle,
}: {
  icon: typeof ImagePlus;
  eyebrow: string;
  title: string;
  subtitle: string;
}) {
  return (
    <header className="flex flex-col items-start gap-3">
      <span className="inline-flex items-center gap-2 rounded-full bg-brand-blue-soft px-3 py-1 text-xs font-semibold text-brand-blue-strong">
        <Icon className="size-3.5" /> {eyebrow}
      </span>
      <h1 className="text-balance font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
        {title}
      </h1>
      <p className="text-base text-muted-foreground sm:text-lg">{subtitle}</p>
    </header>
  );
}

interface FooterProps {
  onPrev?: () => void;
  onNext?: () => void;
  disabledNext?: boolean;
  nextLabel: string;
  hint?: string;
}

function Footer({ onPrev, onNext, disabledNext, nextLabel, hint }: FooterProps) {
  return (
    <div className="sticky bottom-0 -mx-5 mt-2 border-t border-border/60 bg-background/95 px-5 py-4 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-2">
        {hint && (
          <p className="text-center text-xs font-medium text-muted-foreground sm:text-left">
            {hint}
          </p>
        )}
        <div className="flex items-center gap-3">
          {onPrev ? (
            <Button
              type="button"
              variant="ghost"
              size="lg"
              onClick={onPrev}
              className="h-14 rounded-2xl px-5 text-base"
            >
              <ArrowLeft className="mr-1 size-4" /> 이전
            </Button>
          ) : (
            <Button
              asChild
              type="button"
              variant="ghost"
              size="lg"
              className="h-14 rounded-2xl px-5 text-base"
            >
              <Link href="/">
                <ArrowLeft className="mr-1 size-4" /> 홈으로
              </Link>
            </Button>
          )}
          <Button
            type="button"
            size="lg"
            onClick={onNext}
            disabled={disabledNext}
            className="ml-auto h-14 flex-1 rounded-2xl text-base font-bold sm:flex-none sm:px-7 sm:text-lg"
          >
            {nextLabel}
            <ArrowRight className="ml-1 size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
