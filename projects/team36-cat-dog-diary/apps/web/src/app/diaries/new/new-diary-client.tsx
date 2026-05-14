"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { PawPrint, Plus } from "@phosphor-icons/react/dist/ssr";
import { toast } from "sonner";
import type { MoodTag, Pet } from "@cat-dog-diary/shared-types";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  adoptDiary,
  generateDiary,
  regenerateDiary,
  type DiaryStreamCallbacks,
} from "@/lib/api/diaries";
import {
  ALLOWED_MIME,
  MAX_PHOTO_SIZE,
  PhotoUploadError,
  uploadPetPhoto,
} from "@/lib/storage/upload";
import { MOOD_COLOR_VAR } from "@/lib/mood";
import { cn } from "@/lib/utils";

type Step = "input" | "loading" | "result";
type StreamPhase = "preparing" | "analyzing_image" | "writing" | "retrying";

const PHASE_MESSAGE: Record<StreamPhase, string> = {
  preparing: "준비 중...",
  analyzing_image: "사진을 보고 있어요",
  writing: "일기를 쓰고 있어요",
  retrying: "다시 쓰고 있어요",
};

// retry 시 다음 write_diary 시작이 곧바로 phase를 덮어쓰지 않도록 잠깐 lock.
const RETRY_LOCK_MS = 900;

interface ResultState {
  session_id: string;
  generation_id: string;
  diary_text: string;
  short_caption: string;
  mood_tag: MoodTag;
  regenerate_remaining: number;
}

interface NewDiaryClientProps {
  pet: Pet;
  initialNewRemaining: number;
}

export function NewDiaryClient({ pet, initialNewRemaining }: NewDiaryClientProps) {
  const router = useRouter();
  const [step, setStep] = useState<Step>("input");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [photoPath, setPhotoPath] = useState<string | null>(null);
  const [keywords, setKeywords] = useState("");
  const [result, setResult] = useState<ResultState | null>(null);
  const [feedback, setFeedback] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [adopting, setAdopting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [streamPhase, setStreamPhase] = useState<StreamPhase>("preparing");
  const [streamingText, setStreamingText] = useState("");
  const retryLockRef = useRef(false);

  const streamCallbacks: DiaryStreamCallbacks = {
    onNode: (node, phase) => {
      if (phase !== "start") return;
      // safety_check는 너무 짧아 라벨 바꿀 가치 없음 — "일기를 쓰고 있어요" 유지.
      if (node === "analyze_image") setStreamPhase("analyzing_image");
      else if (node === "write_diary") {
        // retry 직후 잠깐은 "다시 쓰고 있어요" 유지.
        if (!retryLockRef.current) setStreamPhase("writing");
      }
    },
    onPartial: (text) => {
      // retry lock 동안 본문이 다시 차오르지 않게 — lock 해제 후부터 노출.
      if (retryLockRef.current) return;
      setStreamingText(text);
    },
    onRetry: () => {
      setStreamPhase("retrying");
      setStreamingText("");
      retryLockRef.current = true;
      window.setTimeout(() => {
        retryLockRef.current = false;
        setStreamPhase("writing");
      }, RETRY_LOCK_MS);
    },
  };

  useEffect(() => {
    if (!previewUrl) return;
    return () => URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  function processFile(f: File) {
    if (!ALLOWED_MIME.includes(f.type as (typeof ALLOWED_MIME)[number])) {
      toast.error("JPG 또는 PNG만 지원해요");
      return;
    }
    if (f.size > MAX_PHOTO_SIZE) {
      toast.error("사진은 10MB 이하여야 해요");
      return;
    }
    setFile(f);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(f));
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) processFile(f);
    e.target.value = "";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) processFile(f);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    if (!isDragging) setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      toast.error("사진을 선택해주세요");
      return;
    }
    const trimmed = keywords.trim();
    if (trimmed.length < 1 || trimmed.length > 1000) {
      toast.error("키워드는 1~1000자로 입력해주세요");
      return;
    }
    setStreamPhase("preparing");
    setStreamingText("");
    setStep("loading");
    try {
      const path = await uploadPetPhoto(file);
      setPhotoPath(path);
      const res = await generateDiary(
        {
          pet_id: pet.id,
          photo_path: path,
          keywords: trimmed,
        },
        streamCallbacks,
      );
      setResult({
        session_id: res.session_id,
        generation_id: res.generation_id,
        diary_text: res.diary_text,
        short_caption: res.short_caption,
        mood_tag: res.mood_tag,
        regenerate_remaining: res.regenerate_remaining,
      });
      setStep("result");
    } catch (err) {
      const msg =
        err instanceof PhotoUploadError
          ? err.message
          : err instanceof Error
            ? err.message
            : "일기 생성 실패";
      toast.error(msg);
      setStep("input");
    }
  }

  async function handleRegenerate() {
    if (!result || !photoPath) return;
    const trimmedFb = feedback.trim();
    if (trimmedFb.length > 500) {
      toast.error("피드백은 500자 이하여야 해요");
      return;
    }
    setStreamPhase("preparing");
    setStreamingText("");
    setStep("loading");
    try {
      const res = await regenerateDiary(
        {
          session_id: result.session_id,
          pet_id: pet.id,
          photo_path: photoPath,
          keywords: keywords.trim(),
          feedback: trimmedFb.length > 0 ? trimmedFb : undefined,
        },
        streamCallbacks,
      );
      setResult({
        ...result,
        generation_id: res.generation_id,
        diary_text: res.diary_text,
        short_caption: res.short_caption,
        mood_tag: res.mood_tag,
        regenerate_remaining: res.regenerate_remaining,
      });
      setFeedback("");
      setShowFeedback(false);
      setStep("result");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "재생성 실패");
      setStep("result");
    }
  }

  async function handleAdopt() {
    if (!result) return;
    setAdopting(true);
    try {
      await adoptDiary({ source_generation_id: result.generation_id });
      toast.success("일기를 추가했어요");
      router.replace("/");
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "채택 실패");
      setAdopting(false);
    }
  }

  if (step === "loading") {
    return (
      <div className="flex flex-col gap-4 py-8">
        <div className="flex items-center gap-3">
          <PawPrint
            size={32}
            weight="duotone"
            className="animate-pulse text-primary"
            aria-hidden
          />
          <p
            key={streamPhase}
            className="text-sm text-muted-foreground animate-in fade-in duration-200"
          >
            {PHASE_MESSAGE[streamPhase]}
          </p>
        </div>
        {streamingText ? (
          <div className="rounded-md border border-border/40 bg-muted/30 p-4 animate-in fade-in duration-200">
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {streamingText}
              <span
                aria-hidden
                className="ml-0.5 inline-block w-[0.45em] -translate-y-[0.05em] animate-pulse text-primary"
              >
                ▋
              </span>
            </p>
          </div>
        ) : null}
      </div>
    );
  }

  if (step === "result" && result) {
    return (
      <div className="flex flex-col gap-5">
        {previewUrl ? (
          <div className="relative w-full overflow-hidden rounded-md shadow-sm">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt={result.short_caption}
              className="aspect-square w-full object-cover"
            />
            <span className="absolute top-4 right-4 inline-flex items-center gap-1.5 rounded-full bg-card/95 px-2.5 py-1 text-xs font-medium shadow-sm backdrop-blur-sm">
              <span
                className="size-1.5 rounded-full"
                style={{ backgroundColor: MOOD_COLOR_VAR[result.mood_tag] }}
                aria-hidden
              />
              {result.mood_tag}
            </span>
          </div>
        ) : null}

        <div className="flex flex-col gap-3 rounded-md border border-border bg-card p-6">
          <h2 className="font-display text-2xl leading-snug sm:text-3xl">
            {result.short_caption}
          </h2>
          <p className="whitespace-pre-wrap text-base leading-relaxed text-foreground/90">
            {result.diary_text}
          </p>
        </div>

        {showFeedback ? (
          <div className="flex flex-col gap-2">
            <Label htmlFor="feedback">어떻게 다르게 써볼까요? (선택)</Label>
            <textarea
              id="feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              maxLength={500}
              rows={3}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="예: 더 차분한 느낌으로 / 산책 얘기는 빼고"
            />
            <div className="flex gap-2">
              <Button
                onClick={handleRegenerate}
                className="flex-1"
                disabled={adopting}
              >
                다시 만들기 ({result.regenerate_remaining}회 남음)
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowFeedback(false);
                  setFeedback("");
                }}
                disabled={adopting}
              >
                취소
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <Button
              onClick={handleAdopt}
              disabled={adopting}
              className="flex-1"
            >
              {adopting ? "저장 중..." : "이 일기로 추가"}
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowFeedback(true)}
              disabled={adopting || result.regenerate_remaining <= 0}
            >
              {result.regenerate_remaining > 0
                ? `다시 만들기 (${result.regenerate_remaining})`
                : "재생성 한도 끝"}
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleGenerate} className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <input
          id="photo"
          type="file"
          accept={ALLOWED_MIME.join(",")}
          onChange={handleFileChange}
          className="sr-only"
        />
        <label
          htmlFor="photo"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            "flex aspect-square w-full cursor-pointer items-center justify-center overflow-hidden rounded-md border-2 border-dashed border-border bg-card/40 transition-all hover:border-primary hover:bg-card focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/30",
            isDragging && "border-primary bg-primary/5 ring-2 ring-primary/30",
            previewUrl && "border-solid",
          )}
        >
          {previewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={previewUrl}
              alt="미리보기"
              draggable={false}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex flex-col items-center gap-3 text-center">
              <Plus
                size={48}
                weight="light"
                className="text-primary"
                aria-hidden
              />
              <span className="text-base font-medium text-foreground">
                클릭하거나 사진을 끌어다 놓으세요
              </span>
              <span className="text-sm text-muted-foreground">
                JPG/PNG · 10MB 이하
              </span>
            </div>
          )}
        </label>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="keywords" className="text-base">
          오늘의 키워드
        </Label>
        <textarea
          id="keywords"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          maxLength={1000}
          rows={4}
          className="w-full rounded-md border border-input bg-card px-4 py-3 text-base"
          placeholder="예: 아침 산책, 처음 본 비둘기에 깜짝, 식빵 굽기"
        />
        <span className="text-sm text-muted-foreground">
          오늘 남은 새 일기 {initialNewRemaining}회
        </span>
      </div>

      <Button
        type="submit"
        size="lg"
        className="h-14 rounded-md text-lg font-medium"
      >
        일기 만들기
      </Button>
    </form>
  );
}
