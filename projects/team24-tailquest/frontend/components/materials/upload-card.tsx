"use client";

import { useRef, useState } from "react";
import { Icon } from "@/components/chrome/icon";
import { cn } from "@/lib/utils";

type Tab = "file" | "github";

const GITHUB_REGEX = /^https?:\/\/github\.com\/[^/]+\/[^/]+/i;

interface Props {
  onUpload: (file: File) => void;
  onGithub: (url: string) => void;
  loading: boolean;
}

export function UploadCard({ onUpload, onGithub, loading }: Props) {
  const [tab, setTab] = useState<Tab>("file");
  const [dragActive, setDragActive] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFiles(files: FileList | File[]) {
    const list = Array.from(files);
    const accepted = list.find(
      (f) =>
        f.name.toLowerCase().endsWith(".pdf") ||
        f.name.toLowerCase().endsWith(".md") ||
        f.type === "application/pdf" ||
        f.type === "text/markdown",
    );
    if (accepted) onUpload(accepted);
  }

  function submitGithub() {
    if (!GITHUB_REGEX.test(repoUrl.trim())) {
      setUrlError("github.com/owner/repo 형식의 URL을 입력해주세요.");
      return;
    }
    setUrlError(null);
    onGithub(repoUrl.trim());
    setRepoUrl("");
  }

  return (
    <section className="rounded-md border border-hairline bg-canvas p-lg flex flex-col gap-md">
      {/* Tab toggle */}
      <div className="flex gap-xs border border-hairline rounded-sm p-xxs self-start">
        <button
          type="button"
          onClick={() => setTab("file")}
          className={cn(
            "text-button-sm px-md py-xs rounded-xs transition-colors",
            tab === "file"
              ? "bg-ink text-on-dark"
              : "text-muted hover:text-ink",
          )}
        >
          파일 업로드
        </button>
        <button
          type="button"
          onClick={() => setTab("github")}
          className={cn(
            "text-button-sm px-md py-xs rounded-xs transition-colors",
            tab === "github"
              ? "bg-ink text-on-dark"
              : "text-muted hover:text-ink",
          )}
        >
          GitHub URL
        </button>
      </div>

      {tab === "file" ? (
        <>
          {/* Drop zone */}
          <div
            role="button"
            tabIndex={0}
            aria-label="파일 업로드 영역"
            onClick={() => !loading && fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if ((e.key === "Enter" || e.key === " ") && !loading)
                fileInputRef.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              if (!loading) setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              if (!loading && e.dataTransfer.files)
                handleFiles(e.dataTransfer.files);
            }}
            className={cn(
              "rounded-md border-2 border-dashed flex flex-col items-center justify-center gap-sm p-xxl cursor-pointer transition-colors",
              loading
                ? "border-hairline bg-surface-soft cursor-wait"
                : dragActive
                  ? "border-ink bg-canvas"
                  : "border-hairline bg-surface-soft hover:border-border-strong",
            )}
          >
            {loading ? (
              <>
                <span className="h-8 w-8 rounded-full border-2 border-hairline border-t-ink animate-spin" />
                <p className="text-body-sm text-muted">업로드 중…</p>
              </>
            ) : (
              <>
                <Icon name="cloud_upload" size={36} className="text-muted" />
                <p className="text-title-sm text-ink">
                  파일을 끌어다 놓거나 클릭하여 업로드
                </p>
                <p className="text-caption-sm text-muted">.pdf · .md 지원 (md 1 MB / pdf 10 MB)</p>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.md,application/pdf,text/markdown"
            className="hidden"
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
          />
        </>
      ) : (
        <>
          <div>
            <p className="text-body-sm text-muted mb-sm">
              Public GitHub 레포 URL을 붙여넣으세요. 마크다운 파일만 자동 인덱싱됩니다.
            </p>
            <div className="flex gap-sm">
              <input
                type="url"
                value={repoUrl}
                disabled={loading}
                onChange={(e) => {
                  setRepoUrl(e.target.value);
                  setUrlError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    submitGithub();
                  }
                }}
                placeholder="https://github.com/owner/repo"
                className="flex-1 text-input"
              />
              <button
                type="button"
                onClick={submitGithub}
                disabled={loading || repoUrl.trim().length === 0}
                className="btn-secondary shrink-0"
              >
                {loading ? (
                  <span className="h-4 w-4 rounded-full border-2 border-hairline border-t-ink animate-spin" />
                ) : (
                  <Icon name="add_link" size={18} />
                )}
                추가
              </button>
            </div>
            {urlError && (
              <p className="text-body-sm text-error-text mt-sm">{urlError}</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}
