"use client";

import { useRef, useState } from "react";

import { Icon } from "@/components/chrome/icon";
import { cn } from "@/lib/utils";
import type { MaterialRef } from "@/lib/onboarding-state";

interface Props {
  materials: MaterialRef[];
  onChange: (m: MaterialRef[]) => void;
}

const GITHUB_REGEX = /^https?:\/\/github\.com\/[^/]+\/[^/]+/i;

export function MaterialUploader({ materials, onChange }: Props) {
  const [repoUrl, setRepoUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function addRepo() {
    if (!GITHUB_REGEX.test(repoUrl)) {
      setUrlError("github.com/owner/repo 형식의 URL을 입력해주세요.");
      return;
    }
    const path = repoUrl.replace(/^https?:\/\/github\.com\//i, "").replace(/\/+$/, "");
    onChange([
      ...materials,
      { kind: "github", name: path, detail: repoUrl },
    ]);
    setRepoUrl("");
    setUrlError(null);
  }

  function addFiles(files: FileList | File[]) {
    const accepted: MaterialRef[] = [];
    for (const f of Array.from(files)) {
      const isPdf = f.name.toLowerCase().endsWith(".pdf") || f.type === "application/pdf";
      const isMd = f.name.toLowerCase().endsWith(".md");
      if (!isPdf && !isMd) continue;
      accepted.push({
        kind: isPdf ? "pdf" : "markdown",
        name: f.name,
        detail: `${(f.size / 1024).toFixed(1)} KB`,
      });
    }
    if (accepted.length > 0) onChange([...materials, ...accepted]);
  }

  function remove(index: number) {
    onChange(materials.filter((_, i) => i !== index));
  }

  return (
    <div className="flex flex-col gap-lg">
      {/* GitHub URL */}
      <section className="rounded-md border border-hairline bg-canvas p-lg">
        <div className="flex items-start gap-md mb-md">
          <span className="h-10 w-10 rounded-md bg-surface-strong text-ink flex items-center justify-center shrink-0">
            <Icon name="code" size={20} />
          </span>
          <div className="flex-1">
            <h3 className="text-title-md text-ink">GitHub 레포지토리 추가</h3>
            <p className="text-body-sm text-muted mt-1">
              예: <code className="text-ink">ksundong/backend-interview-question</code> — 마크다운 질문집을 자동 인덱싱합니다.
            </p>
          </div>
        </div>
        <div className="flex gap-sm">
          <input
            type="url"
            value={repoUrl}
            onChange={(e) => {
              setRepoUrl(e.target.value);
              setUrlError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addRepo();
              }
            }}
            placeholder="https://github.com/owner/repo"
            className="flex-1 text-input"
          />
          <button type="button" onClick={addRepo} className="btn-secondary shrink-0">
            <Icon name="add_link" size={18} />
            추가
          </button>
        </div>
        {urlError && (
          <p className="text-body-sm text-error-text mt-sm">{urlError}</p>
        )}
      </section>

      {/* File drop zone */}
      <section className="rounded-md border border-hairline bg-canvas p-lg">
        <div className="flex items-start gap-md mb-md">
          <span className="h-10 w-10 rounded-md bg-surface-strong text-ink flex items-center justify-center shrink-0">
            <Icon name="upload_file" size={20} />
          </span>
          <div className="flex-1">
            <h3 className="text-title-md text-ink">PDF · Markdown 업로드</h3>
            <p className="text-body-sm text-muted mt-1">
              본인이 정리한 노트, 강의 자료, 면접 후기 등을 업로드하세요. 파일당 최대 5MB.
            </p>
          </div>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            if (e.dataTransfer.files) addFiles(e.dataTransfer.files);
          }}
          onClick={() => fileInput.current?.click()}
          role="button"
          tabIndex={0}
          className={cn(
            "rounded-md border-2 border-dashed bg-surface-soft p-xxl flex flex-col items-center justify-center gap-sm cursor-pointer transition-colors",
            dragActive ? "border-ink bg-canvas" : "border-hairline hover:border-ink",
          )}
        >
          <Icon name="cloud_upload" size={40} className="text-ink" />
          <p className="text-title-sm text-ink">
            파일을 끌어다 놓거나 클릭하여 업로드
          </p>
          <p className="text-caption-sm text-muted">.pdf · .md 형식 지원</p>
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.md,application/pdf,text/markdown"
            multiple
            className="hidden"
            onChange={(e) => e.target.files && addFiles(e.target.files)}
          />
        </div>
      </section>

      {/* Selected materials list */}
      {materials.length > 0 && (
        <section>
          <h4 className="text-title-sm text-ink mb-md flex items-center gap-sm">
            <Icon name="check_circle" size={16} className="text-rausch" filled />
            추가된 자료 {materials.length}건
          </h4>
          <ul className="flex flex-col gap-sm">
            {materials.map((m, i) => (
              <li
                key={i}
                className="flex items-center gap-md rounded-sm border border-hairline bg-canvas p-md"
              >
                <Icon
                  name={
                    m.kind === "github"
                      ? "code"
                      : m.kind === "pdf"
                        ? "picture_as_pdf"
                        : "markdown"
                  }
                  size={18}
                  className="text-ink shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-body-sm text-ink truncate">{m.name}</p>
                  {m.detail && (
                    <p className="text-caption-sm text-muted truncate">
                      {m.detail}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => remove(i)}
                  className="text-muted hover:text-ink transition-colors p-1"
                  aria-label={`${m.name} 제거`}
                >
                  <Icon name="close" size={18} />
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
