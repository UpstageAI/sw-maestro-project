"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { Sparkles, Check, Loader2 } from "lucide-react";
import type { AgentTrace } from "@/lib/types";

const STEP_ORDER = [
  { key: "CopyWriter", label: "홍보 문구 작성 중..." },
  { key: "ImageGenerator", label: "카드 이미지 만드는 중..." },
  { key: "Verifier", label: "내용 한 번 더 확인 중..." },
  // Decorative tail spinner — pipeline never emits "FetchResult" so it stays
  // active until wizard receives status:done and unmounts this view.
  { key: "FetchResult", label: "결과 가져오는 중..." },
];

interface ProcessingStepProps {
  startedAt: number;
  agentTrace: AgentTrace[];
  attempt?: number;
}

function elapsedLabel(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}초 경과`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}분 ${r}초 경과`;
}

export function ProcessingStep({ startedAt, agentTrace, attempt }: ProcessingStepProps) {
  const [now, setNow] = useState<number>(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    const tick = () => {
      if (!active) return;
      setNow(Date.now());
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      active = false;
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Use only the latest attempt's trace so retry visualization restarts the row spinners.
  // Each attempt begins with a fresh CopyWriter entry (graph re-routes verifier→copyWriter on retry).
  let lastCopyWriterIdx = 0;
  for (let i = agentTrace.length - 1; i >= 0; i--) {
    if (agentTrace[i].step === "CopyWriter") {
      lastCopyWriterIdx = i;
      break;
    }
  }
  const currentTrace = agentTrace.slice(lastCopyWriterIdx);
  const seenSteps = new Set(currentTrace.map((t) => t.step));
  const firstUndoneIdx = STEP_ORDER.findIndex((s) => !seenSteps.has(s.key));
  const derivedAttempt =
    attempt ?? agentTrace.filter((t) => t.step === "CopyWriter").length;

  return (
    <div className="mx-auto flex w-full max-w-md flex-col items-center gap-10 px-5 py-12 text-center">
      <div className="relative grid size-32 place-items-center">
        <motion.span
          aria-hidden
          className="absolute inset-0 rounded-full border-4 border-brand-blue/20"
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.span
          aria-hidden
          className="absolute inset-3 rounded-full border-4"
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          style={{
            borderTopColor: "var(--brand-blue)",
            borderRightColor: "transparent",
            borderBottomColor: "transparent",
            borderLeftColor: "transparent",
          }}
        />
        <Sparkles className="size-10 text-brand-blue" strokeWidth={2.2} />
      </div>

      <div>
        <h2 className="font-display text-2xl font-extrabold tracking-tight">
          홍보 카드뉴스를 만들고 있어요
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          약 2~3분 정도 걸려요. 잠시만 기다려 주세요.
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {now > 0 ? elapsedLabel(now - startedAt) : "0초 경과"}
          {derivedAttempt > 1 ? ` · 다시 만드는 중 (${derivedAttempt}회차)` : ""}
        </p>
      </div>

      <ol className="w-full space-y-2 text-left">
        {STEP_ORDER.map((s, i) => {
          const isDone = seenSteps.has(s.key);
          const isActive = !isDone && i === firstUndoneIdx;
          return (
            <motion.li
              key={s.key}
              animate={{ opacity: isDone ? 1 : 0.55 }}
              className="flex items-center gap-3 rounded-2xl border border-border/60 bg-card px-4 py-3 toss-shadow"
            >
              <span
                className={
                  "grid size-8 shrink-0 place-items-center rounded-full " +
                  (isDone
                    ? "bg-brand-blue text-white"
                    : "bg-muted text-muted-foreground")
                }
              >
                {isDone ? (
                  <Check className="size-4" />
                ) : (
                  <Loader2
                    className={
                      "size-4 " + (isActive ? "animate-spin" : "")
                    }
                  />
                )}
              </span>
              <span className="text-sm font-medium text-foreground">
                {s.label}
              </span>
            </motion.li>
          );
        })}
      </ol>

    </div>
  );
}
