"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, Loader2 } from "lucide-react";
import { motion } from "motion/react";

import { Button } from "@/components/ui/button";
import {
  ApiError,
  generateReport,
  getJob,
  pollJob,
  type GenerateReportResult,
  type Report,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = ["역량", "경험", "문제해결", "협업", "적합성"];

function scoreLabel(score: number): string {
  if (score >= 4.0) return "우수";
  if (score >= 3.0) return "양호";
  if (score >= 2.0) return "보강 필요";
  return "재학습 권장";
}

export default function ReportPage() {
  const router = useRouter();
  const [report, setReport] = React.useState<Report | null>(null);
  const [progress, setProgress] = React.useState(0);
  const [message, setMessage] = React.useState<string>(
    "리포트 생성을 시작하는 중입니다.",
  );
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const sid = sessionStorage.getItem("interview.session_id");
    if (!sid) {
      router.replace("/upload");
      return;
    }
    const ctrl = new AbortController();

    const onProgress = (job: { progress: number; message: string }) => {
      setProgress(job.progress);
      if (job.message) setMessage(job.message);
    };

    /**
     * 리포트 요청.
     * - 409 (busy_job_id) 응답이면 busy job 종류에 따라 자동 처리:
     *   - generate_report 인 경우 그 job 결과를 그대로 사용 (이미 생성됨)
     *   - 다른 job 이면 끝까지 기다린 뒤 다시 generateReport 시도
     */
    const fetchReport = async (): Promise<GenerateReportResult> => {
      try {
        const start = await generateReport(sid, true);
        return await pollJob<GenerateReportResult>(start.job_id, {
          intervalMs: 1500,
          signal: ctrl.signal,
          onProgress,
        });
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          const detail = e.detail as
            | { detail?: { busy_job_id?: string } }
            | undefined;
          const busyId = detail?.detail?.busy_job_id;
          if (busyId) {
            const busy = await getJob(busyId);
            if (busy.job_type === "generate_report") {
              return await pollJob<GenerateReportResult>(busyId, {
                intervalMs: 1500,
                signal: ctrl.signal,
                onProgress,
              });
            }
            // 다른 job 끝나길 기다린 뒤 다시 generateReport
            await pollJob(busyId, {
              intervalMs: 1500,
              signal: ctrl.signal,
            }).catch(() => undefined);
            const start = await generateReport(sid, true);
            return await pollJob<GenerateReportResult>(start.job_id, {
              intervalMs: 1500,
              signal: ctrl.signal,
              onProgress,
            });
          }
        }
        throw e;
      }
    };

    const run = async () => {
      try {
        const result = await fetchReport();
        setReport(result.report);
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        const msg =
          e instanceof ApiError
            ? `${e.status}: ${e.message}`
            : e instanceof Error
              ? e.message
              : "리포트 생성 실패";
        setError(msg);
      }
    };
    void run();
    return () => ctrl.abort();
  }, [router]);

  if (error) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col items-center gap-4 px-4 py-32 text-center">
        <AlertCircle className="size-6 text-destructive" />
        <h1 className="text-xl font-semibold">
          리포트 생성 중 문제가 발생했어요.
        </h1>
        <p className="text-sm text-muted-foreground">{error}</p>
        <Button
          variant="outline"
          onClick={() => router.replace("/upload")}
          className="rounded-full"
        >
          처음부터 다시
        </Button>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col gap-8 px-4 py-32">
        <div className="flex flex-col items-center gap-3 text-center">
          <Loader2 className="size-5 animate-spin text-accent" />
          <h1 className="text-2xl font-semibold tracking-tight">
            리포트를 만들고 있어요.
          </h1>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <motion.div
            className="h-full bg-primary"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>
      </div>
    );
  }

  const orderedCategories = CATEGORY_ORDER.filter(
    (c) => c in report.category_scores,
  ).map((c) => ({ name: c, score: report.category_scores[c] }));

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-16 px-4 py-16 sm:px-6 sm:py-20">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex flex-col gap-3"
      >
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          Step 04 · 종합 리포트
        </p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          면접이 끝났습니다.
        </h1>
        <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
          STAR · 구체성 · 직무 관련성 · 일관성 네 축으로 답변을 진단하고, 자주
          드러난 약점과 개선 방향을 정리했습니다.
        </p>
      </motion.div>

      <OverallScore score={report.overall_score} />
      <CategoryScores categories={orderedCategories} />
      <WeaknessSummary tags={report.weakness_summary} />
      <CoachingCard text={report.improvement_suggestions} />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5 }}
        className="flex flex-col gap-3 border-t border-border/60 pt-12 sm:flex-row"
      >
        <Button
          asChild
          size="lg"
          className="rounded-full px-7 transition-transform hover:scale-105"
        >
          <Link
            href="/upload"
            onClick={() => {
              sessionStorage.removeItem("interview.session_id");
              sessionStorage.removeItem("interview.start_job_id");
            }}
          >
            새 면접 시작
            <ArrowRight className="ml-1 size-4" />
          </Link>
        </Button>
        <Button
          asChild
          variant="outline"
          size="lg"
          className="rounded-full px-7"
        >
          <Link href="/">처음으로</Link>
        </Button>
      </motion.div>
    </div>
  );
}

function OverallScore({ score }: { score: number }) {
  const percentage = Math.min(100, (score / 5) * 100);
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6 }}
      className="flex flex-col items-center gap-5 rounded-3xl border border-border/60 bg-card p-8 text-center sm:p-12"
    >
      <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        Overall Score
      </p>
      <div className="flex items-baseline gap-1">
        <p className="text-6xl font-bold tracking-tight sm:text-7xl">
          {score.toFixed(2)}
        </p>
        <p className="text-2xl text-muted-foreground sm:text-3xl">/5</p>
      </div>
      <p className="text-sm font-medium text-muted-foreground">
        {scoreLabel(score)}
      </p>
      <div className="h-1.5 w-full max-w-md overflow-hidden rounded-full bg-muted">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${percentage}%` }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 1, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="h-full bg-primary"
        />
      </div>
    </motion.section>
  );
}

function CategoryScores({
  categories,
}: {
  categories: { name: string; score: number }[];
}) {
  if (categories.length === 0) return null;
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6 }}
      className="flex flex-col gap-6"
    >
      <div className="flex flex-col gap-1">
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          Category Scores
        </p>
        <h2 className="text-xl font-semibold tracking-tight">
          카테고리별 평균
        </h2>
      </div>
      <div className="flex flex-col gap-4">
        {categories.map((c, i) => (
          <motion.div
            key={c.name}
            initial={{ opacity: 0, x: -8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
            className="flex flex-col gap-1.5"
          >
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-sm font-medium">{c.name}</p>
              <p className="font-mono text-sm">
                {c.score.toFixed(2)}
                <span className="text-muted-foreground">/5</span>
              </p>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${(c.score / 5) * 100}%` }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{
                  duration: 0.8,
                  delay: 0.2 + i * 0.08,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="h-full bg-primary"
              />
            </div>
          </motion.div>
        ))}
      </div>
    </motion.section>
  );
}

function WeaknessSummary({ tags }: { tags: string[] }) {
  if (tags.length === 0) return null;
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6 }}
      className="flex flex-col gap-4"
    >
      <div className="flex flex-col gap-1">
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          Weakness Summary
        </p>
        <h2 className="text-xl font-semibold tracking-tight">
          자주 드러난 약점{" "}
          <span className="text-sm font-normal text-muted-foreground">
            · Top {tags.length}
          </span>
        </h2>
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, i) => (
          <motion.span
            key={tag}
            initial={{ opacity: 0, scale: 0.92 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.3, delay: i * 0.06 }}
            className={cn(
              "rounded-full border px-3 py-1.5 text-sm font-medium",
              i === 0
                ? "border-warning/40 bg-warning/15 text-warning"
                : "border-border/60 bg-muted text-muted-foreground",
            )}
          >
            {tag}
          </motion.span>
        ))}
      </div>
    </motion.section>
  );
}

function CoachingCard({ text }: { text: string }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6 }}
      className="flex flex-col gap-4"
    >
      <div className="flex flex-col gap-1">
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          Coaching
        </p>
        <h2 className="text-xl font-semibold tracking-tight">
          다음 면접에서 바꿀 행동
        </h2>
      </div>
      <div className="rounded-2xl border-y border-r border-l-2 border-y-border/60 border-l-accent border-r-border/60 bg-card p-6 sm:p-8">
        <p className="whitespace-pre-line text-sm leading-relaxed sm:text-base">
          {text}
        </p>
      </div>
    </motion.section>
  );
}
