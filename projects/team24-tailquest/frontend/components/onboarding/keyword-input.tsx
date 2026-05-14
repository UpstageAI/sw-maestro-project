"use client";

import { useState } from "react";

import { Icon } from "@/components/chrome/icon";

interface Props {
  values: string[];
  onChange: (next: string[]) => void;
  /** Hard cap on number of keywords (default 8). */
  max?: number;
}

/** Chip-style free-text keyword input for step 2 of onboarding.
 *  Used so users can request "Kubernetes" / "gRPC" / "WebRTC" etc. that
 *  aren't in the curated domain catalog. */
export function KeywordInput({ values, onChange, max = 8 }: Props) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const atMax = values.length >= max;

  function add() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    if (trimmed.length > 30) {
      setError("키워드는 30자 이하로 입력해주세요.");
      return;
    }
    if (values.some((v) => v.toLowerCase() === trimmed.toLowerCase())) {
      setError("이미 추가된 키워드입니다.");
      return;
    }
    if (atMax) {
      setError(`최대 ${max}개까지 추가할 수 있습니다.`);
      return;
    }
    onChange([...values, trimmed]);
    setDraft("");
    setError(null);
  }

  function remove(idx: number) {
    onChange(values.filter((_, i) => i !== idx));
  }

  return (
    <div className="rounded-md border border-hairline bg-canvas p-md">
      <div className="flex items-center justify-between mb-sm">
        <p className="text-title-sm text-ink">키워드 직접 입력</p>
        {max > 1 && (
          <span className="text-caption-sm text-muted">
            {values.length} / {max}
          </span>
        )}
      </div>
      <p className="text-caption-sm text-muted mb-sm">
        목록에 없는 주제를 직접 입력하세요. 예: <span className="text-ink">Kubernetes</span>,{" "}
        <span className="text-ink">gRPC</span>,{" "}
        <span className="text-ink">WebRTC</span>
      </p>

      <div className="flex gap-sm">
        <input
          type="text"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setError(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          disabled={atMax}
          placeholder={
            atMax
              ? max === 1
                ? "이미 입력됨 — 변경하려면 위 칩을 삭제하세요"
                : `최대 ${max}개에 도달했습니다`
              : "키워드 입력 후 Enter"
          }
          maxLength={30}
          className="flex-1 bg-canvas border border-hairline focus:border-ink rounded-sm px-md py-sm text-body-md text-ink placeholder:text-muted-soft outline-none transition-colors"
        />
        <button
          type="button"
          onClick={add}
          disabled={atMax || draft.trim().length === 0}
          className="btn-secondary shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Icon name="add" size={18} />
          추가
        </button>
      </div>

      {error && (
        <p className="text-body-sm text-error-text mt-sm">{error}</p>
      )}

      {values.length > 0 && (
        <ul className="flex flex-wrap gap-1 mt-md">
          {values.map((v, i) => (
            <li key={i}>
              <button
                type="button"
                onClick={() => remove(i)}
                className="pill bg-rausch text-on-primary hover:bg-rausch-active transition-colors group"
              >
                <span>{v}</span>
                <Icon
                  name="close"
                  size={12}
                  className="opacity-70 group-hover:opacity-100"
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
