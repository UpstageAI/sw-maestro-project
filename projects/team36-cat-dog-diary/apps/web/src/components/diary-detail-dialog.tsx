"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { Diary } from "@cat-dog-diary/shared-types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { deleteDiary } from "@/lib/api/diaries";
import { MOOD_COLOR_VAR } from "@/lib/mood";

interface DiaryDetailDialogProps {
  diary: Diary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const FULL_DATE_FMT = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "long",
  day: "numeric",
});

type View = "detail" | "sns-preview";

interface Capture {
  url: string;
  file: File;
}

function pad(n: number, w = 2): string {
  return String(n).padStart(w, "0");
}

function generateFilename(): string {
  const d = new Date();
  return `냥멍일기-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(
    d.getDate(),
  )}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}.png`;
}

export function DiaryDetailDialog({
  diary,
  open,
  onOpenChange,
}: DiaryDetailDialogProps) {
  const router = useRouter();
  const [view, setView] = useState<View>("detail");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [capture, setCapture] = useState<Capture | null>(null);

  const dateLabel = FULL_DATE_FMT.format(new Date(diary.created_at));

  function resetAll() {
    setView("detail");
    setConfirmDelete(false);
    if (capture) {
      URL.revokeObjectURL(capture.url);
      setCapture(null);
    }
  }

  function handleOpenChange(o: boolean) {
    if (deleting || fetching) return;
    if (!o) resetAll();
    onOpenChange(o);
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteDiary(diary.id);
      toast.success("일기를 지웠어요");
      onOpenChange(false);
      resetAll();
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "삭제 실패");
      setDeleting(false);
    }
  }

  // 'sns-preview' 진입 시 서버에서 PNG fetch.
  useEffect(() => {
    if (view !== "sns-preview") return;
    let cancelled = false;
    let createdUrl: string | null = null;

    async function run() {
      setFetching(true);
      try {
        const res = await fetch(`/api/diaries/${diary.id}/sns-image`);
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(
            body?.error?.message ?? `이미지 생성 실패 (${res.status})`,
          );
        }
        const blob = await res.blob();
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        createdUrl = url;
        const file = new File([blob], generateFilename(), {
          type: "image/png",
        });
        setCapture({ url, file });
      } catch (err) {
        if (!cancelled) {
          toast.error(
            err instanceof Error ? err.message : "이미지 생성 실패",
          );
          setView("detail");
        }
      } finally {
        if (!cancelled) setFetching(false);
      }
    }

    run();
    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [view, diary.id]);

  function handleDownload() {
    if (!capture) return;
    const a = document.createElement("a");
    a.href = capture.url;
    a.download = capture.file.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success("이미지를 저장했어요");
  }

  async function handleShare() {
    if (!capture) return;
    if (!navigator.canShare?.({ files: [capture.file] })) {
      toast.error("이 기기에서는 공유를 지원하지 않아요");
      return;
    }
    try {
      await navigator.share({
        files: [capture.file],
        title: diary.short_caption,
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      toast.error("공유 실패");
    }
  }

  // share files 지원 여부는 디바이스 capability — capture 결과와 무관하게 mount 시 한 번 결정.
  // capture와 묶으면 로딩→완료 시점에 버튼 레이아웃이 바뀌어 어색.
  const [supportsShareFiles, setSupportsShareFiles] = useState(false);
  useEffect(() => {
    if (typeof navigator === "undefined" || !navigator.canShare) return;
    const probe = new File([new Uint8Array(0)], "probe.png", {
      type: "image/png",
    });
    setSupportsShareFiles(navigator.canShare({ files: [probe] }));
  }, []);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogTitle className="sr-only">{diary.short_caption}</DialogTitle>
        <DialogDescription className="sr-only">{dateLabel}</DialogDescription>

        {view === "detail" ? (
          <div className="flex flex-col gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={diary.photo_signed_url}
              alt={diary.short_caption}
              className="aspect-square w-full rounded-xl bg-muted object-cover"
            />

            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-muted/60 px-2.5 py-1 text-xs font-medium">
                <span
                  className="size-1.5 rounded-full"
                  style={{ backgroundColor: MOOD_COLOR_VAR[diary.mood_tag] }}
                  aria-hidden
                />
                {diary.mood_tag}
              </span>
              <span className="text-sm font-medium">{diary.short_caption}</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {dateLabel}
              </span>
            </div>

            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {diary.diary_text}
            </p>

            <div className="flex flex-col gap-2 border-t pt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setView("sns-preview")}
                className="w-full"
              >
                SNS 이미지로 저장
              </Button>

              {!confirmDelete ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmDelete(true)}
                  className="w-full"
                >
                  일기 삭제
                </Button>
              ) : (
                <div className="flex flex-col gap-2">
                  <p className="text-sm">정말 지울까요? 되돌릴 수 없어요.</p>
                  <div className="flex gap-2">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleDelete}
                      disabled={deleting}
                      className="flex-1"
                    >
                      {deleting ? "삭제 중..." : "삭제 확정"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDelete(false)}
                      disabled={deleting}
                      className="flex-1"
                    >
                      취소
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (capture) {
                    URL.revokeObjectURL(capture.url);
                    setCapture(null);
                  }
                  setView("detail");
                }}
                disabled={fetching}
              >
                ← 뒤로
              </Button>
            </div>

            <div className="flex min-h-[300px] items-center justify-center rounded-xl bg-muted/40 p-2">
              {fetching || !capture ? (
                <div className="flex flex-col items-center gap-2 py-12 text-sm text-muted-foreground">
                  <span className="size-6 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
                  이미지 만드는 중...
                </div>
              ) : (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={capture.url}
                  alt="SNS 미리보기"
                  className="max-h-[70vh] w-auto rounded-md object-contain shadow-md"
                />
              )}
            </div>

            <div className="flex gap-2 border-t pt-3">
              {supportsShareFiles ? (
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleShare}
                  disabled={fetching || !capture}
                  className="flex-1"
                >
                  SNS 공유
                </Button>
              ) : null}
              <Button
                variant={supportsShareFiles ? "outline" : "default"}
                size="sm"
                onClick={handleDownload}
                disabled={fetching || !capture}
                className="flex-1"
              >
                다운로드
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
