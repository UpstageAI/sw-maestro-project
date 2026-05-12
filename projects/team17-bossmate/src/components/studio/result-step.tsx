"use client";

import Image from "next/image";
import { useMemo, useState } from "react";
import { motion } from "motion/react";
import {
  Copy,
  Check,
  Sparkles,
  RotateCcw,
  PencilLine,
  Download,
  ShieldCheck,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { GeneratedContent } from "@/lib/types";

interface ResultStepProps {
  result: GeneratedContent;
  busy: boolean;
  onRegenerate: (feedback?: string) => void;
  onEdit: () => void;
  onRestart: () => void;
}

function buildCaption(result: GeneratedContent): string {
  const lines = [result.copyText.trim()];
  if (result.hashtags.length) {
    lines.push("", result.hashtags.map((t) => (t.startsWith("#") ? t : `#${t}`)).join(" "));
  }
  return lines.join("\n");
}

export function ResultStep({
  result,
  busy,
  onRegenerate,
  onEdit,
  onRestart,
}: ResultStepProps) {
  const caption = useMemo(() => buildCaption(result), [result]);
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState("");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(caption);
      setCopied(true);
      toast.success("홍보 문구를 복사했어요.");
      setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error("복사에 실패했어요. 직접 선택해 주세요.");
    }
  };

  const handleDownload = () => {
    const url = result.mockImage.dataUrl;
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.request.store.storeName || "promo"}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const verification = result.verification;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mx-auto w-full max-w-3xl space-y-10 px-5 py-8"
    >
      <header className="flex flex-col gap-3 text-center sm:text-left">
        <div className="inline-flex items-center justify-center gap-2 self-center rounded-full bg-brand-blue-soft px-3 py-1 text-xs font-semibold text-brand-blue-strong sm:self-start">
          <Sparkles className="size-3.5" />
          완성됐어요
        </div>
        <h2 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          {result.request.store.storeName}님의 홍보물입니다.
        </h2>
        <p className="text-base text-muted-foreground">
          이미지 한 장과 SNS 캡션을 함께 만들어 드렸어요. 마음에 들지 않으면
          피드백을 적고 다시 생성하세요.
        </p>
      </header>

      <section className="overflow-hidden rounded-3xl border border-border/70 bg-card toss-shadow">
        <div className="relative aspect-square w-full bg-muted">
          <Image
            src={result.mockImage.dataUrl}
            alt={`${result.request.store.storeName} 홍보 이미지`}
            fill
            sizes="(min-width: 768px) 600px, 100vw"
            className="object-cover"
            unoptimized
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/60 px-5 py-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            {verification && !verification.skipped && (
              <Badge
                variant={verification.ok ? "default" : "destructive"}
                className="rounded-full"
              >
                {verification.ok ? (
                  <>
                    <ShieldCheck className="mr-1 size-3" /> 내용 확인 완료
                  </>
                ) : (
                  <>
                    <ShieldAlert className="mr-1 size-3" /> 누락 항목 있음
                  </>
                )}
              </Badge>
            )}
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleDownload}
            className="rounded-full"
          >
            <Download className="mr-1.5 size-4" /> 이미지 저장
          </Button>
        </div>
      </section>

      {verification && !verification.skipped && verification.missing.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-semibold">검증에서 누락된 키워드</p>
          <p className="mt-1">{verification.missing.join(", ")}</p>
        </div>
      )}

      <section className="rounded-3xl border border-border/70 bg-card p-6 toss-shadow sm:p-8">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-display text-lg font-bold tracking-tight">
            홍보 문구 (SNS 캡션)
          </h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="rounded-full"
          >
            {copied ? (
              <>
                <Check className="mr-1.5 size-4" /> 복사됨
              </>
            ) : (
              <>
                <Copy className="mr-1.5 size-4" /> 문구 복사
              </>
            )}
          </Button>
        </div>
        <pre className="mt-4 whitespace-pre-wrap break-keep rounded-2xl bg-muted/60 p-5 text-sm leading-relaxed text-foreground sm:text-base">
{caption}
        </pre>
      </section>

      {result.hashtags.length > 0 && (
        <section className="rounded-3xl border border-border/70 bg-card p-6 toss-shadow sm:p-8">
          <h3 className="font-display text-lg font-bold tracking-tight">
            추천 해시태그
          </h3>
          <div className="mt-4 flex flex-wrap gap-2">
            {result.hashtags.map((t) => (
              <span
                key={t}
                className="rounded-full bg-brand-blue-soft px-3 py-1.5 text-sm font-medium text-brand-blue-strong"
              >
                {t.startsWith("#") ? t : `#${t}`}
              </span>
            ))}
          </div>
        </section>
      )}

      <section className="rounded-3xl border border-border/70 bg-card p-6 toss-shadow sm:p-8">
        <h3 className="font-display text-lg font-bold tracking-tight">
          피드백을 주고 다시 만들기
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          예) &ldquo;더 따뜻하게&rdquo;, &ldquo;할인 금액을 강조해줘&rdquo;, &ldquo;이모지 줄여줘&rdquo;
        </p>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="수정이 필요한 점을 적어주세요"
          maxLength={200}
          rows={3}
          className="mt-3 w-full rounded-2xl border border-border/60 bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/40"
        />
        <Button
          type="button"
          variant="default"
          size="lg"
          disabled={busy}
          onClick={() => onRegenerate(feedback.trim() || undefined)}
          className="mt-3 h-12 w-full rounded-2xl text-base font-semibold"
        >
          <RotateCcw className="mr-1.5 size-4" />
          {busy ? "다시 만드는 중..." : "피드백 반영해서 다시 만들기"}
        </Button>
      </section>

      <Separator />

      <div className="flex flex-col gap-5 pb-16">
        <div className="grid gap-2 sm:grid-cols-2">
          <Button
            type="button"
            variant="outline"
            size="lg"
            onClick={onEdit}
            className="h-14 w-full rounded-2xl text-base"
          >
            <PencilLine className="mr-1.5 size-4" />
            가게 정보 수정
          </Button>
          <Button
            type="button"
            size="lg"
            onClick={onRestart}
            className="h-14 w-full rounded-2xl text-base font-bold"
          >
            <RotateCcw className="mr-1.5 size-4" />
            처음부터 다시 만들기
          </Button>
        </div>
        <p className="text-center text-xs text-muted-foreground">
          마음에 드는 결과가 나올 때까지 피드백을 주고 다시 만들 수 있어요.
        </p>
      </div>
    </motion.div>
  );
}
