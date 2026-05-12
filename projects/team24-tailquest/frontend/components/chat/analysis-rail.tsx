"use client";

import { useState } from "react";

import { Icon } from "@/components/chrome/icon";
import { cn } from "@/lib/utils";
import type { Turn } from "@/lib/chat-state";
import type { AnswerQuality, Chunk, MaterialResponse, Severity } from "@/lib/api";
import type { Domain } from "@/lib/domains";

const SEVERITY_TONE: Record<Severity, string> = {
  critical: "bg-rausch text-on-primary",
  moderate: "bg-ink text-on-dark",
  minor: "bg-surface-strong text-ink",
};

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "핵심 누락",
  moderate: "보통",
  minor: "경미",
};

const QUALITY_TONE: Record<AnswerQuality, string> = {
  good: "bg-ink text-on-dark",
  uncertain: "bg-surface-strong text-ink",
  incorrect: "bg-rausch text-on-primary",
};

const QUALITY_LABEL: Record<AnswerQuality, string> = {
  good: "충실",
  uncertain: "모름·짧음",
  incorrect: "오답",
};

interface Props {
  turns: Turn[];
  selectedTurnId: string | null;
  onSelect: (id: string) => void;
  domains: Domain[];
  keywords: string[];
  /** Materials snapshot for the active session — rendered in the "이 세션의 자료"
   *  card so the user can see at a glance which uploads this session is using. */
  sessionMaterials?: MaterialResponse[];
}

export function AnalysisRail({
  turns,
  selectedTurnId,
  onSelect,
  domains,
  keywords,
  sessionMaterials = [],
}: Props) {
  const totalScope = domains.length + keywords.length;
  const analyzed = turns.filter((t) => t.notes !== undefined);

  return (
    <aside className="h-full flex flex-col min-h-0 overflow-hidden gap-md">
      {/* Header — always pinned */}
      <section className="rounded-md border border-hairline bg-canvas p-md shrink-0">
        <p className="text-uppercase-tag text-rausch mb-1">현재 세션</p>
        <h3 className="text-title-md text-ink mb-sm">
          {totalScope === 0
            ? "면접 연습"
            : totalScope === 1
              ? domains[0]?.label ?? keywords[0]
              : `${totalScope}개 주제`}
        </h3>
        <div className="flex items-center justify-between text-caption-sm text-muted">
          <span>총 {turns.length}개 질문</span>
          <span>분석 완료 {analyzed.length}건</span>
        </div>
        {totalScope > 1 && (
          <ul className="flex flex-wrap gap-1 mt-sm">
            {domains.map((d) => (
              <li key={d.id} className="pill bg-surface-strong text-ink">
                {d.label}
              </li>
            ))}
            {keywords.map((kw) => (
              <li
                key={`kw-${kw}`}
                className="pill bg-rausch text-on-primary"
                title="사용자 지정 키워드"
              >
                {kw}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Scrollable body */}
      <div
        className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden scrollbar-thin flex flex-col gap-md"
        style={{ scrollbarGutter: "stable" }}
      >
        {/* 분석 이력 — always at top, lists every turn (analyzed or not).
            Each entry collapses by default and expands to show question
            intent + answer-quality verdict + notes + retrieved-context.
            "이 세션의 자료" stays as a separate card below. */}
        {turns.length === 0 ? (
          <section className="rounded-md border border-dashed border-hairline bg-surface-soft p-md text-center">
            <Icon name="psychology_alt" size={28} className="text-muted mb-1" />
            <p className="text-body-sm text-muted">
              질문을 받으면 여기에 분석 이력이 쌓입니다.
            </p>
          </section>
        ) : (
          <section className="flex flex-col gap-sm">
            <p className="text-uppercase-tag text-muted px-sm">분석 이력</p>
            {turns.map((t, i) => (
              <HistoryEntryCard
                key={t.id}
                turnNumber={i + 1}
                turn={t}
                isSelected={t.id === selectedTurnId}
                onSelect={() => onSelect(t.id)}
              />
            ))}
          </section>
        )}

        {sessionMaterials.length > 0 && (
          <SessionMaterialsCard materials={sessionMaterials} />
        )}
      </div>
    </aside>
  );
}

function HistoryEntryCard({
  turnNumber,
  turn,
  isSelected,
  onSelect,
}: {
  turnNumber: number;
  turn: Turn;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const [open, setOpen] = useState(false);
  const analyzed = turn.notes !== undefined;
  const hasContext =
    !!turn.retrievedContext && turn.retrievedContext.length > 0;

  return (
    <section
      className={cn(
        "rounded-md border bg-canvas transition-colors",
        isSelected ? "border-ink" : "border-hairline",
      )}
    >
      <button
        type="button"
        onClick={() => {
          setOpen((o) => !o);
          onSelect();
        }}
        aria-expanded={open}
        className="w-full flex items-center gap-sm px-md py-sm hover:bg-surface-soft transition-colors text-left"
      >
        <span className="text-caption-sm text-muted tabular-nums w-6 shrink-0">
          {String(turnNumber).padStart(2, "0")}
        </span>
        <span className="text-body-sm text-ink truncate flex-1 min-w-0">
          {turn.question || "질문 준비 중"}
        </span>
        {turn.answerQuality && (
          <span className={cn("pill shrink-0", QUALITY_TONE[turn.answerQuality])}>
            {QUALITY_LABEL[turn.answerQuality]}
          </span>
        )}
        {!analyzed && (
          <span className="pill bg-surface-strong text-muted shrink-0">대기</span>
        )}
        <Icon
          name={open ? "expand_less" : "expand_more"}
          size={18}
          className="text-muted shrink-0"
        />
      </button>

      {open && (
        <div className="px-md pb-md pt-0 flex flex-col gap-md border-t border-hairline">
          <div className="pt-sm">
            <p className="text-uppercase-tag text-muted mb-1">질문</p>
            <p className="text-body-sm text-body italic break-keep whitespace-pre-wrap">
              &quot;{turn.question}&quot;
            </p>
          </div>

          {/* 답변 퀄리티 평가 — 점수는 표시하지 않음 (수치 노출 시 사용자가
              점수 자체에 집착하는 부작용 회피). pill 라벨만 보여줌. */}
          {turn.answerQuality && (
            <div>
              <p className="text-uppercase-tag text-muted mb-1">답변 평가</p>
              <span className={cn("pill", QUALITY_TONE[turn.answerQuality])}>
                {QUALITY_LABEL[turn.answerQuality]}
              </span>
            </div>
          )}

          {/* 질문 의도 */}
          {turn.questionIntent && (
            <div>
              <div className="flex items-center gap-sm mb-1">
                <Icon name="track_changes" size={14} className="text-rausch" />
                <p className="text-uppercase-tag text-muted">질문의 의도</p>
              </div>
              <p className="text-body-sm text-ink leading-relaxed break-keep whitespace-pre-wrap">
                {turn.questionIntent}
              </p>
            </div>
          )}

          {/* notes */}
          {turn.notes && turn.notes.length > 0 && (
            <div>
              <p className="text-uppercase-tag text-muted mb-sm">
                약점 노트 ({turn.notes.length}건)
              </p>
              <ul className="flex flex-col gap-sm">
                {turn.notes.map((n, i) => (
                  <li key={i} className="border-l-2 border-hairline pl-md">
                    <div className="flex items-center gap-sm flex-wrap mb-1">
                      <span className={cn("pill", SEVERITY_TONE[n.severity])}>
                        {SEVERITY_LABEL[n.severity]}
                      </span>
                      <span className="text-body-sm text-ink font-semibold break-keep">
                        {n.label}
                      </span>
                    </div>
                    {n.detail && (
                      <p className="text-caption text-muted leading-relaxed break-keep">
                        {n.detail}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 참조 자료 */}
          {hasContext && (
            <div>
              <p className="text-uppercase-tag text-muted mb-sm">
                참조 자료 ({turn.retrievedContext!.length}건)
              </p>
              <ul className="flex flex-col gap-sm">
                {turn.retrievedContext!.map((c, i) => (
                  <li key={i} className="border-l-2 border-hairline pl-md">
                    <div className="flex items-center gap-xs mb-xxs flex-wrap">
                      {c.source === "web" && c.url ? (
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-caption-sm text-legal-link hover:underline truncate flex items-center gap-xxs"
                        >
                          <span
                            className="material-symbols-outlined shrink-0"
                            style={{ fontSize: 12 }}
                          >
                            open_in_new
                          </span>
                          {c.file_name}
                        </a>
                      ) : (
                        <p className="text-caption-sm text-muted truncate">
                          {c.file_name}
                          {c.heading ? `#${c.heading}` : ""}
                        </p>
                      )}
                      {c.source === "user" && (
                        <span className="pill bg-surface-strong text-ink shrink-0">
                          내 자료
                        </span>
                      )}
                      {c.source === "web" && (
                        <span className="pill bg-surface-strong text-muted shrink-0">
                          웹
                        </span>
                      )}
                    </div>
                    <p className="text-body-sm text-ink leading-relaxed break-keep line-clamp-3">
                      {trimChunkExcerpt(c.text, turn.question)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!analyzed && !turn.questionIntent && (
            <p className="text-caption-sm text-muted italic">
              아직 답변 분석이 완료되지 않았습니다. 답변을 제출하면 의도·퀄리티·노트가 채워집니다.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/** Korean particles to peel off the tail of a question token so
 *  "Spring와" / "프로세스의" still hit raw chunk text. */
const KO_PARTICLES = [
  "에서의", "에서는", "에서도", "와의", "과의",
  "에서", "에는", "에도",
  "와", "과", "을", "를", "이", "가", "은", "는",
  "의", "에", "로", "으로", "도", "만", "이나", "나",
];

/** Question-form filler words that should not drive matching. */
const STOP_TOKENS = new Set([
  "설명", "해주세요", "주세요", "주실래요", "본인", "한번", "대해",
  "어떻게", "무엇", "왜", "있나요", "있을까요", "있어요", "혹시",
  "들어", "보셨어요", "들어보셨어요", "한번", "이해",
  "the", "a", "an", "is", "are", "of", "to", "and", "or",
]);

/** Pull content tokens out of a question:
 *   - English/numeric runs ≥2 chars (TCP, Spring, Boot, IoC)
 *   - Korean nouns ≥2 chars after stripping trailing particles
 *  Stopwords are removed so question-form fluff doesn't anchor the excerpt. */
function extractQuestionTokens(question: string): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const matches = question.match(/[가-힣]+|[A-Za-z][A-Za-z0-9]+/g) ?? [];
  for (const raw of matches) {
    let t = raw;
    if (/^[가-힣]/.test(t)) {
      for (const p of KO_PARTICLES) {
        if (t.endsWith(p) && t.length > p.length + 1) {
          t = t.slice(0, -p.length);
          break;
        }
      }
    }
    const lower = t.toLowerCase();
    if (lower.length < 2 || STOP_TOKENS.has(lower)) continue;
    if (seen.has(lower)) continue;
    seen.add(lower);
    out.push(lower);
  }
  return out;
}

/** Find the slice of a Chroma chunk that's actually relevant to `question`.
 *
 *  Strategy:
 *   1. Tokenize the question (drop particles + stopwords)
 *   2. Split chunk into paragraphs, score each by token-overlap count
 *   3. Pick the highest-scoring paragraph
 *   4. If matches exist, anchor a `max`-char window on the first matching
 *      token so the keyword sits near the middle of the excerpt
 *   5. Fallback to the first paragraph when nothing matches (e.g. citation
 *      attached for an off-topic chunk)
 *
 *  Output is capped at `max` chars; surrounding `line-clamp-3` then visually
 *  trims long single-line paragraphs.
 */
function trimChunkExcerpt(raw: string, question: string, max = 240): string {
  const cleaned = raw.replace(/\r\n/g, "\n").trim();
  if (!cleaned) return "";

  const paragraphs = cleaned.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
  if (paragraphs.length === 0) return "";

  const tokens = question ? extractQuestionTokens(question) : [];
  let bestPara = paragraphs[0];
  let bestScore = 0;

  if (tokens.length > 0) {
    for (const p of paragraphs) {
      const lower = p.toLowerCase();
      let score = 0;
      for (const t of tokens) {
        if (lower.includes(t)) score++;
      }
      if (score > bestScore) {
        bestScore = score;
        bestPara = p;
      }
    }
  }

  const collapsed = bestPara.replace(/\s+/g, " ").trim();
  if (collapsed.length <= max) return collapsed;

  // Window the excerpt on the first matching token so the anchor sits
  // roughly in the middle of the visible slice.
  let anchor = -1;
  if (bestScore > 0) {
    const lower = collapsed.toLowerCase();
    for (const t of tokens) {
      const i = lower.indexOf(t);
      if (i >= 0 && (anchor === -1 || i < anchor)) anchor = i;
    }
  }
  if (anchor === -1) {
    return collapsed.slice(0, max).trimEnd() + " …";
  }

  const half = Math.floor(max / 2);
  let start = Math.max(0, anchor - half);
  let end = start + max;
  if (end > collapsed.length) {
    end = collapsed.length;
    start = Math.max(0, end - max);
  }
  let excerpt = collapsed.slice(start, end).trim();
  if (start > 0) excerpt = "… " + excerpt;
  if (end < collapsed.length) excerpt = excerpt.trimEnd() + " …";
  return excerpt;
}

function SessionMaterialsCard({ materials }: { materials: MaterialResponse[] }) {
  return (
    <section className="rounded-md border border-hairline bg-canvas p-md">
      <div className="flex items-center justify-between mb-sm">
        <p className="text-uppercase-tag text-muted">이 세션의 자료</p>
        <span className="text-caption-sm text-muted">{materials.length}건</span>
      </div>
      <ul className="flex flex-col gap-1">
        {materials.map((m) => (
          <li
            key={m.id}
            className="flex items-center gap-sm text-body-sm text-ink"
          >
            <Icon
              name={m.kind === "github" ? "code" : "description"}
              size={16}
              className="text-muted shrink-0"
            />
            <span className="truncate flex-1 min-w-0">{m.name}</span>
            {m.status !== "ready" && (
              <span className="pill bg-surface-strong text-muted shrink-0">
                {m.status}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

// Kept exported indirectly — Chunk type used by HistoryEntryCard's retrievedContext loop.
export type { Chunk };
