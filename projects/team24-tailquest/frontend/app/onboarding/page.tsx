"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Icon } from "@/components/chrome/icon";
import { DomainGrid } from "@/components/onboarding/domain-grid";
import { KeywordInput } from "@/components/onboarding/keyword-input";
import { StepProgress } from "@/components/onboarding/step-progress";
import { TrackCard } from "@/components/onboarding/track-card";

import { clearChatTurns } from "@/lib/chat-state";
import { TRACKS, type Track } from "@/lib/domains";
import {
  getSelectedMaterialIds,
  reconcileSelectedMaterials,
} from "@/lib/materials-selection";
import { clearOnboarding, saveOnboarding } from "@/lib/onboarding-state";

const STEPS = [
  { id: 1, label: "트랙 선택" },
  { id: 2, label: "도메인 선택" },
];

/** Onboarding wizard — bound to viewport height so the action bar at the
 *  bottom is always visible regardless of step content size. The middle
 *  section scrolls internally only when its content actually exceeds the
 *  available area (e.g., zoomed-in or tiny laptops). */
export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [track, setTrack] = useState<Track | null>(null);
  const [domainIds, setDomainIds] = useState<string[]>([]);
  const [customKeywords, setCustomKeywords] = useState<string[]>([]);
  // Latches once "자료 선택하러 가기" is clicked so a rapid second click can't
  // double-route to /materials.
  const [starting, setStarting] = useState(false);

  // Wipe any previously-saved onboarding state on mount. Entering /onboarding
  // means "I'm starting a fresh session" — if we leave the old state in
  // sessionStorage and the user navigates back to /chat without finishing
  // (e.g. browser back), /chat would re-seed using the stale prior selection.
  // Also reconcile the selected-materials sessionStorage against the BE list
  // so dead IDs from a wiped Chroma don't follow the user into the next step.
  useEffect(() => {
    clearOnboarding();
    clearChatTurns();
    reconcileSelectedMaterials().catch(() => {
      // BE unreachable — leave whatever's in sessionStorage; /materials will
      // re-reconcile when it loads.
    });
  }, []);

  const trackData = track ? TRACKS[track] : null;
  // Step 2 enforces XOR: pick *exactly one* of (domain OR keyword), not both.
  const hasOneSelection =
    (domainIds.length === 1 && customKeywords.length === 0) ||
    (domainIds.length === 0 && customKeywords.length === 1);
  const canAdvance =
    (step === 1 && track !== null) || (step === 2 && hasOneSelection);

  function next() {
    if (!canAdvance) return;
    if (step < 2) {
      setStep((s) => s + 1);
      return;
    }
    finish();
  }

  function back() {
    if (step > 1) setStep((s) => s - 1);
  }

  /** Persist the onboarding draft and route to /materials.
   *  /materials owns the final "면접 시작 → /chat" handoff (it lets the user
   *  pick which uploaded materials to attach to this session, or skip). */
  function finish() {
    if (starting) return;
    if (!track || !hasOneSelection) return;
    setStarting(true);
    saveOnboarding({
      track,
      domainIds,
      customKeywords,
      materials: [],
      materialIds: getSelectedMaterialIds(),
      completedAt: new Date().toISOString(),
    });
    router.push("/materials");
  }

  return (
    <main className="flex-1 min-h-0 bg-canvas flex flex-col overflow-hidden">
      {/* Step progress strip — pinned top */}
      <div className="shrink-0 max-w-airbnb mx-auto px-xl pt-md pb-sm w-full">
        <StepProgress steps={STEPS} current={step} />
      </div>

      {/* Scrollable content body */}
      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin">
        {step === 1 && <Step1Track track={track} onSelect={setTrack} />}
        {step === 2 && trackData && (
          <Step2Domains
            trackLabel={trackData.label}
            domains={trackData.domains}
            selected={domainIds}
            // XOR — picking a domain clears any typed keyword and vice versa.
            // Re-selecting the active domain deselects (returns []).
            onToggle={(id) => {
              setDomainIds((prev) => (prev.includes(id) ? [] : [id]));
              setCustomKeywords([]);
            }}
            keywords={customKeywords}
            onKeywordsChange={(next) => {
              setCustomKeywords(next);
              if (next.length > 0) setDomainIds([]);
            }}
          />
        )}
      </div>

      {/* Action bar — pinned bottom, never clipped */}
      <div className="shrink-0 border-t border-hairline bg-canvas">
        <div className="max-w-airbnb mx-auto px-xl py-md flex items-center justify-between gap-md">
          <button
            type="button"
            onClick={back}
            disabled={step === 1}
            className="btn-tertiary-text disabled:invisible"
          >
            ← 이전
          </button>

          <div className="flex items-center gap-md">
            {step < 2 ? (
              <button
                type="button"
                onClick={next}
                disabled={!canAdvance}
                className="btn-primary"
              >
                다음
                <Icon name="arrow_forward" size={18} />
              </button>
            ) : (
              <button
                type="button"
                onClick={finish}
                disabled={!canAdvance || starting}
                className="btn-primary flex items-center gap-sm"
              >
                <Icon name="folder_open" size={18} />
                {starting ? "이동 중…" : "자료 선택하러 가기"}
              </button>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

// ---------- Step 1 ----------

function Step1Track({
  track,
  onSelect,
}: {
  track: Track | null;
  onSelect: (t: Track) => void;
}) {
  return (
    <section className="max-w-4xl mx-auto px-xl py-lg">
      <header className="text-center mb-lg">
        <p className="text-uppercase-tag text-rausch mb-1">1 / 3 — 트랙</p>
        <h1 className="text-display-lg text-ink">
          어떤 면접을 준비하시나요?
        </h1>
        <p className="text-body-sm text-muted mt-sm max-w-2xl mx-auto">
          기초 CS 지식 트랙과 실제 사용한 기술 스택 트랙은 출제 패턴이 다릅니다.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
        <TrackCard
          trackId="cs"
          label={TRACKS.cs.label}
          description={TRACKS.cs.description}
          icon={TRACKS.cs.icon}
          examples={TRACKS.cs.domains.slice(0, 5).map((d) => d.label)}
          selected={track === "cs"}
          onSelect={() => onSelect("cs")}
        />
        <TrackCard
          trackId="stack"
          label={TRACKS.stack.label}
          description={TRACKS.stack.description}
          icon={TRACKS.stack.icon}
          examples={TRACKS.stack.domains.slice(0, 5).map((d) => d.label)}
          selected={track === "stack"}
          onSelect={() => onSelect("stack")}
        />
      </div>
    </section>
  );
}

// ---------- Step 2 ----------

function Step2Domains({
  trackLabel,
  domains,
  selected,
  onToggle,
  keywords,
  onKeywordsChange,
}: {
  trackLabel: string;
  domains: ReturnType<typeof TRACKS.cs.domains.slice>;
  selected: string[];
  onToggle: (id: string) => void;
  keywords: string[];
  onKeywordsChange: (next: string[]) => void;
}) {
  const activeDomain = selected[0] ?? null;
  const activeKeyword = keywords[0] ?? null;
  const summary =
    activeDomain
      ? `선택: ${domains.find((d) => d.id === activeDomain)?.label ?? activeDomain} (분야)`
      : activeKeyword
        ? `선택: ${activeKeyword} (직접 입력 키워드)`
        : null;
  return (
    <section className="max-w-airbnb mx-auto px-xl py-lg">
      <header className="text-center mb-md">
        <p className="text-uppercase-tag text-rausch mb-1">
          2 / 2 — {trackLabel}
        </p>
        <h1 className="text-display-lg text-ink">
          어떤 분야를 다루시겠어요?
        </h1>
        <p className="text-body-sm text-muted mt-sm max-w-2xl mx-auto">
          아래 분야 중 하나를 고르거나, 목록에 없으면 키워드를 직접 입력하세요.
          <strong className="text-ink"> 둘 중 하나만</strong> 선택할 수 있습니다.
        </p>
      </header>

      <DomainGrid
        domains={domains}
        selected={selected}
        onToggle={onToggle}
      />

      <div className="my-md flex items-center gap-sm">
        <span className="flex-1 h-px bg-hairline" />
        <span className="text-caption-sm text-muted">또는 키워드 직접 입력</span>
        <span className="flex-1 h-px bg-hairline" />
      </div>

      <KeywordInput values={keywords} onChange={onKeywordsChange} max={1} />

      {summary && (
        <p className="text-body-sm text-ink mt-md text-center">{summary}</p>
      )}
    </section>
  );
}

