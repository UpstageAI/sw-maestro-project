"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Check, Loader2 } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import { Button } from "@/components/ui/button";
import { pollJob, type StartSessionResult } from "@/lib/api";

export default function AnalyzingPage() {
  const router = useRouter();
  const [progress, setProgress] = React.useState(0);
  const [step, setStep] = React.useState<string>("queued");
  const [message, setMessage] = React.useState<string>(
    "작업을 큐에 등록하는 중입니다.",
  );
  const [error, setError] = React.useState<string | null>(null);
  const [done, setDone] = React.useState(false);

  React.useEffect(() => {
    const jobId = sessionStorage.getItem("interview.start_job_id");
    if (!jobId) {
      router.replace("/upload");
      return;
    }
    const ctrl = new AbortController();

    const run = async () => {
      try {
        const result = await pollJob<StartSessionResult>(jobId, {
          intervalMs: 1500,
          signal: ctrl.signal,
          onProgress: (job) => {
            setProgress(job.progress);
            setStep(job.step);
            setMessage(job.message);
          },
        });
        // 세션 ID 저장 + 면접 화면으로
        sessionStorage.setItem(
          "interview.session_id",
          result.session.session_id,
        );
        sessionStorage.removeItem("interview.start_job_id");
        setDone(true);
        setTimeout(() => router.push("/interview"), 800);
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setError((e as Error).message);
      }
    };
    void run();

    return () => ctrl.abort();
  }, [router]);

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-10 px-4 py-24 sm:py-32">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {error
            ? "분석 중 문제가 발생했어요."
            : done
              ? "면접 준비 완료."
              : "자료를 분석하고 있어요."}
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {error
            ? "잠시 후 다시 시도해 주세요."
            : done
              ? "잠시 후 첫 질문이 시작됩니다."
              : "회사·직무에 맞춘 질문을 만들기 위해 자료를 정리하는 중입니다."}
        </p>
      </div>

      {/* Progress bar */}
      <div className="flex flex-col gap-3">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="h-full bg-primary"
          />
        </div>
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="font-mono uppercase tracking-wider text-muted-foreground">
            {step}
          </span>
          <span className="font-mono text-muted-foreground">{progress}%</span>
        </div>
      </div>

      {/* Status card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${error ? "err" : done ? "done" : "run"}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
          className="flex items-start gap-3 rounded-2xl border border-border/60 bg-card p-5"
        >
          {error ? (
            <AlertCircle className="size-5 shrink-0 text-destructive" />
          ) : done ? (
            <Check
              className="size-5 shrink-0 text-primary"
              strokeWidth={3}
            />
          ) : (
            <Loader2 className="size-5 shrink-0 animate-spin text-accent" />
          )}
          <p className="text-sm leading-relaxed">
            {error ?? message}
          </p>
        </motion.div>
      </AnimatePresence>

      {error && (
        <Button
          variant="outline"
          onClick={() => router.replace("/upload")}
          className="rounded-full"
        >
          처음부터 다시 시작
        </Button>
      )}
    </div>
  );
}
