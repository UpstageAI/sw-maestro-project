"use client";
import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [showExtra, setShowExtra] = useState(false);
  const [weeklyHours, setWeeklyHours] = useState("");
  const [age, setAge] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const router = useRouter();

  function pickFile(f: File | null) {
    if (!f) return;
    if (f.size > 10 * 1024 * 1024) {
      setError("파일은 10MB 이하만 업로드할 수 있어요.");
      return;
    }
    setError(null);
    setFile(f);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file) {
      setError("계약서 파일을 선택해주세요.");
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    if (weeklyHours) fd.append("weekly_hours", weeklyHours);
    if (age) fd.append("age", age);
    startTransition(async () => {
      try {
        const res = await fetch("/api/upload", { method: "POST", body: fd });
        if (!res.ok) {
          const t = await res.text();
          throw new Error(t || `HTTP ${res.status}`);
        }
        const { id } = (await res.json()) as { id: string };
        router.push(`/analysis/${id}`);
      } catch (err) {
        setError((err as Error).message || "업로드에 실패했어요.");
      }
    });
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      {error && (
        <div className="flex items-start gap-2 rounded-xl bg-danger-bg p-3 text-danger">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 shrink-0" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <p className="text-[13px] font-medium leading-5">{error}</p>
        </div>
      )}

      <div>
        <label
          htmlFor="contract-file"
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            const f = e.dataTransfer.files?.[0];
            if (f) pickFile(f);
          }}
          className={`group flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center cursor-pointer transition-colors ${
            drag
              ? "border-toss-blue bg-toss-blue-bg"
              : file
                ? "border-grey-200 bg-white"
                : "border-grey-300 bg-grey-50 hover:border-toss-blue hover:bg-toss-blue-bg"
          }`}
        >
          {!file ? (
            <>
              <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-toss-blue-bg text-toss-blue group-hover:scale-105 transition-transform">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </span>
              <p className="mt-4 text-[15px] font-bold text-grey-900">
                여기에 파일을 끌어다 놓거나 <span className="text-toss-blue">클릭</span>
              </p>
              <p className="mt-1 text-[13px] text-grey-500">PDF · JPG · PNG · 최대 10MB</p>
            </>
          ) : (
            <div className="w-full flex items-center gap-3 text-left">
              <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-toss-blue-bg text-toss-blue">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-semibold text-grey-900 truncate">{file.name}</p>
                <p className="text-[12px] text-grey-500">{fmtSize(file.size)}</p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  setFile(null);
                  if (inputRef.current) inputRef.current.value = "";
                }}
                className="shrink-0 rounded-full bg-grey-100 hover:bg-grey-200 px-3 py-1.5 text-[12px] font-semibold text-grey-700"
              >
                변경
              </button>
            </div>
          )}
        </label>
        <input
          id="contract-file"
          ref={inputRef}
          type="file"
          accept="application/pdf,image/*"
          className="sr-only"
          onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="rounded-2xl bg-white border border-grey-200">
        <button
          type="button"
          onClick={() => setShowExtra((v) => !v)}
          className="flex w-full items-center justify-between px-5 py-4 text-left"
          aria-expanded={showExtra}
        >
          <span>
            <span className="block text-[14px] font-semibold text-grey-900">추가 정보 입력하기</span>
            <span className="block text-[12px] text-grey-500">근로시간·나이를 알려주시면 더 정확해져요 (선택)</span>
          </span>
          <svg
            width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
            className={`text-grey-400 transition-transform ${showExtra ? "rotate-180" : ""}`}
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        {showExtra && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 px-5 pb-5">
            <Field
              label="실제 주당 근로시간"
              placeholder="예: 45"
              suffix="시간"
              value={weeklyHours}
              onChange={setWeeklyHours}
            />
            <Field
              label="나이"
              placeholder="예: 25"
              suffix="세"
              value={age}
              onChange={setAge}
            />
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={pending || !file}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-toss-blue text-white font-semibold text-[16px] py-4 hover:bg-toss-blue-hover active:bg-toss-blue-pressed disabled:bg-grey-200 disabled:text-grey-400 disabled:cursor-not-allowed transition-colors"
      >
        {pending ? (
          <>
            <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
            파일 업로드 중...
          </>
        ) : (
          <>
            분석 시작하기
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </>
        )}
      </button>

      <p className="flex items-center justify-center gap-1.5 text-[12px] text-grey-500">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
        업로드된 파일은 분석 후 자동 폐기됩니다.
      </p>
    </form>
  );
}

function Field({
  label, value, onChange, placeholder, suffix,
}: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; suffix?: string }) {
  return (
    <div>
      <label className="block text-[13px] font-medium text-grey-700 mb-1.5">{label}</label>
      <div className="relative">
        <input
          type="number"
          inputMode="numeric"
          min={0}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="block w-full h-12 rounded-xl border border-grey-200 bg-white px-4 pr-12 text-[15px] font-medium text-grey-900 placeholder-grey-400 focus:border-toss-blue focus:bg-white focus:outline-none transition-colors"
        />
        {suffix && (
          <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-[13px] font-medium text-grey-500">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}
