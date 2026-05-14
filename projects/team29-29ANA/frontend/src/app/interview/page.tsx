"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Loader2, Send, Sparkles } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  getSession,
  pollJob,
  submitAnswer,
  type ProcessAnswerResult,
  type Question,
  type SessionSummary,
} from "@/lib/api";

const MIN_ANSWER_LENGTH = 50;
type Phase = "loading" | "asking" | "evaluating" | "generating" | "error";

export default function InterviewPage() {
  const router = useRouter();
  // sessionId 는 mutable ref 로 — effect body 에서 setState 룰 회피
  const sidRef = React.useRef<string | null>(null);
  const [session, setSession] = React.useState<SessionSummary | null>(null);
  const [question, setQuestion] = React.useState<Question | null>(null);
  const [answer, setAnswer] = React.useState("");
  const [phase, setPhase] = React.useState<Phase>("loading");
  const [progressMsg, setProgressMsg] = React.useState<string>("");
  const [error, setError] = React.useState<string | null>(null);
  const [retryHint, setRetryHint] = React.useState<string | null>(null);

  // 1. 진입 시 세션 정보 로드
  React.useEffect(() => {
    const sid = sessionStorage.getItem("interview.session_id");
    if (!sid) {
      router.replace("/upload");
      return;
    }
    sidRef.current = sid;
    getSession(sid)
      .then((s) => {
        setSession(s);
        if (!s.current_question) {
          setError("현재 질문을 받지 못했습니다.");
          setPhase("error");
          return;
        }
        setQuestion(s.current_question);
        setPhase("asking");
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "세션 조회 실패");
        setPhase("error");
      });
  }, [router]);

  const ansLen = answer.trim().length;
  const canSubmit =
    phase === "asking" && ansLen >= MIN_ANSWER_LENGTH && !!question;
  const canReport = session?.can_report === true;

  // 평가/생성 phase 동안 경과 시간 — 사용자가 "멈춘 건지" 의심하지 않도록
  const [elapsedSec, setElapsedSec] = React.useState(0);
  React.useEffect(() => {
    const id = setInterval(() => {
      setElapsedSec((s) =>
        phase === "evaluating" || phase === "generating" ? s + 1 : 0,
      );
    }, 1000);
    return () => clearInterval(id);
  }, [phase]);

  const formatElapsed = (s: number) => {
    const mm = Math.floor(s / 60);
    const ss = s % 60;
    return mm > 0 ? `${mm}분 ${ss}초` : `${ss}초`;
  };

  const onSubmit = async () => {
    const sid = sidRef.current;
    if (!canSubmit || !sid || !question) return;
    setRetryHint(null);

    try {
      // 1) 답변 제출 → job_id 받음
      setPhase("evaluating");
      setProgressMsg("답변을 평가하고 있어요");
      const start = await submitAnswer(sid, question.id, answer);

      // 2) job polling — onProgress 로 message 갱신, generating phase 전환
      const result = await pollJob<ProcessAnswerResult>(start.job_id, {
        onProgress: (job) => {
          // job.step 또는 message 에 따라 phase 결정
          if (job.message) setProgressMsg(job.message);
          if (
            job.step?.includes("generat") ||
            job.step?.includes("question")
          ) {
            setPhase("generating");
          }
        },
      });

      // 3) action 분기
      switch (result.action) {
        case "retry":
          setRetryHint(result.message ?? "답변이 너무 짧습니다.");
          // 같은 질문 유지
          if (result.question) setQuestion(result.question);
          setPhase("asking");
          break;
        case "force_end": {
          // 자동 리포트 — 세션 ID 그대로 두고 report 페이지로
          if (result.session) setSession(result.session);
          router.push("/report");
          return;
        }
        case "followup":
        case "next_question":
        case "can_report":
          if (result.session) setSession(result.session);
          if (result.question) {
            setQuestion(result.question);
            setAnswer("");
          }
          setPhase("asking");
          break;
      }
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.status}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "알 수 없는 오류";
      setError(msg);
      setPhase("error");
    }
  };

  const buttonLabel =
    phase === "evaluating"
      ? "답변 평가 중…"
      : phase === "generating"
        ? "다음 질문 준비 중…"
        : "답변 제출";

  if (phase === "loading") {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col items-center gap-3 px-4 py-32 text-center">
        <Loader2 className="size-5 animate-spin text-accent" />
        <p className="text-sm text-muted-foreground">세션을 불러오는 중…</p>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col items-center gap-4 px-4 py-32 text-center">
        <AlertCircle className="size-6 text-destructive" />
        <h1 className="text-xl font-semibold">문제가 발생했어요.</h1>
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

  if (!question || !session) return null;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 px-4 py-12 sm:px-6 sm:py-16">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          묶음 {session.bundle_count + 1} · 질문 {session.question_count + 1}
        </p>
        {canReport && phase === "asking" && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/report")}
            className="rounded-full"
          >
            리포트 먼저 보기
          </Button>
        )}
      </div>

      {/* Progress bar (bundle 기준) */}
      <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full bg-primary"
          initial={{ width: 0 }}
          animate={{
            width: `${Math.min(
              100,
              ((session.bundle_count + (canReport ? 0.5 : 0)) /
                Math.max(session.min_bundles_for_report, 1)) *
                100,
            )}%`,
          }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      {/* Question or Loading card */}
      <AnimatePresence mode="wait">
        {phase === "asking" ? (
          <motion.div
            key={`q-${question.id}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col gap-5 rounded-2xl border border-border/60 bg-card p-6 sm:p-8"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-accent/30 bg-accent/10 px-2.5 py-0.5 text-xs font-medium text-accent">
                {question.category}
              </span>
              {question.is_followup && (
                <span className="rounded-full border border-warning/30 bg-warning/10 px-2.5 py-0.5 text-xs font-medium text-warning">
                  꼬리질문
                </span>
              )}
            </div>
            <p className="text-xl font-medium leading-relaxed sm:text-2xl">
              {question.text}
            </p>
            {retryHint && (
              <div className="flex items-start gap-2 rounded-xl border border-warning/30 bg-warning/10 p-3 text-xs text-warning">
                <AlertCircle className="size-4 shrink-0" />
                <span>{retryHint}</span>
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key={`loading-${phase}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card p-6 sm:p-8"
          >
            <div className="flex items-center gap-3">
              {phase === "evaluating" ? (
                <Loader2 className="size-5 animate-spin text-accent" />
              ) : (
                <motion.div
                  animate={{ rotate: [0, 12, -8, 0], scale: [1, 1.1, 1] }}
                  transition={{ duration: 1.6, repeat: Infinity }}
                  className="text-accent"
                >
                  <Sparkles className="size-5" />
                </motion.div>
              )}
              <h3 className="text-lg font-medium">
                {phase === "evaluating"
                  ? "답변을 평가하고 있어요"
                  : "다음 질문을 준비 중이에요"}
              </h3>
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {progressMsg ||
                (phase === "evaluating"
                  ? "STAR 구조 · 구체성 · 직무 관련성 · 일관성 네 축으로 답변을 살펴보고 있습니다."
                  : "답변에서 더 깊이 파고들 지점을 찾아 다음 질문을 만들고 있어요.")}
            </p>
            <div className="flex items-center justify-between gap-3 border-t border-border/40 pt-3">
              <p className="font-mono text-xs text-muted-foreground">
                경과 {formatElapsed(elapsedSec)}
              </p>
              {elapsedSec >= 60 && (
                <p className="text-xs text-warning">
                  예상보다 오래 걸리네요. 답변이 길면 평가에 시간이 더 걸릴 수 있어요.
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Answer form */}
      <motion.div
        animate={{ opacity: phase === "asking" ? 1 : 0.4 }}
        transition={{ duration: 0.3 }}
        className={
          phase !== "asking"
            ? "pointer-events-none flex flex-col gap-3"
            : "flex flex-col gap-3"
        }
      >
        <Textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="구체적인 사례·수치·역할을 포함해 답변해주세요. STAR(상황·과제·행동·결과) 흐름이면 더 좋습니다."
          rows={6}
          className="min-h-[160px] resize-y"
          disabled={phase !== "asking"}
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            {ansLen}자 / 최소 {MIN_ANSWER_LENGTH}자
          </p>
          <Button
            onClick={onSubmit}
            disabled={!canSubmit}
            size="lg"
            className="rounded-full px-6 transition-transform hover:scale-105 disabled:hover:scale-100"
          >
            {buttonLabel}
            {phase === "asking" && <Send className="ml-1 size-4" />}
          </Button>
        </div>
      </motion.div>
    </div>
  );
}
