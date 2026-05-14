"use client";

import * as React from "react";
import { FileText, Upload, X } from "lucide-react";

import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  label: string;
  description?: string;
  file: File | null;
  onChange: (file: File | null) => void;
  accept?: string;
}

export function FileDropzone({
  label,
  description,
  file,
  onChange,
  accept = ".pdf",
}: FileDropzoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleFile = (f: File | null) => {
    setError(null);
    if (!f) {
      onChange(null);
      return;
    }
    const ext = accept.replace(".", "").toLowerCase();
    if (!f.name.toLowerCase().endsWith(`.${ext}`)) {
      setError(`${ext.toUpperCase()} 파일만 업로드할 수 있어요.`);
      return;
    }
    onChange(f);
  };

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium">{label}</p>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files[0];
          if (f) handleFile(f);
        }}
        className={cn(
          "group flex min-h-[110px] cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border/80 bg-card/30 p-6 transition-colors",
          "hover:border-accent/60 hover:bg-accent/5",
          "focus:outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-ring/40",
          dragOver && "border-accent bg-accent/10",
          file && "border-solid border-border bg-card/70",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />

        {file ? (
          <div
            className="flex w-full items-center justify-between gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex min-w-0 items-center gap-3">
              <FileText className="size-5 shrink-0 text-primary" />
              <div className="flex min-w-0 flex-col">
                <p className="truncate text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
            <button
              type="button"
              aria-label="파일 삭제"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
              }}
              className="shrink-0 rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          </div>
        ) : (
          <>
            <Upload className="size-5 text-muted-foreground transition-colors group-hover:text-accent" />
            <p className="text-sm font-medium">
              드래그하거나 클릭해서 PDF 업로드
            </p>
            <p className="text-xs text-muted-foreground">
              PDF 파일만 지원합니다.
            </p>
          </>
        )}
      </div>

      {error && (
        <p className="text-xs font-medium text-destructive">{error}</p>
      )}
    </div>
  );
}
