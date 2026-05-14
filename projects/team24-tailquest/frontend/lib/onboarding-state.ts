// Persisted onboarding result. Stored in sessionStorage so the practice page
// can pick it up after the wizard completes.

import type { Track } from "@/lib/domains";

const STORAGE_KEY = "tq.onboarding";

export interface MaterialRef {
  /** Display name (filename or repo path) */
  name: string;
  kind: "github" | "pdf" | "markdown";
  /** GitHub URL for `kind=github`; for files we keep size as a placeholder
   *  (Phase 2 will actually upload + index). */
  detail?: string;
}

export interface OnboardingState {
  track: Track;
  domainIds: string[];
  /** Free-form user keywords typed in step 2 (e.g. "Kubernetes", "gRPC").
   *  Treated equivalently to selected domains by the backend. */
  customKeywords: string[];
  materials: MaterialRef[];
  /** IDs of MaterialResponse objects the user selected on /materials.
   *  Stored separately from `materials` (which holds legacy local refs).
   *  Passed to /sessions as material_ids for RAG retrieval. */
  materialIds?: string[];
  /** Set when the user has completed the wizard at least once. */
  completedAt?: string;
}

export function loadOnboarding(): OnboardingState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as OnboardingState) : null;
  } catch {
    return null;
  }
}

export function saveOnboarding(s: OnboardingState): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

export function clearOnboarding(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STORAGE_KEY);
}
