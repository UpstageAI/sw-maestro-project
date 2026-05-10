// Persisted "selected materials" state — single source of truth for which
// uploaded materials the user wants the next interview session to use as RAG
// context. Stored in sessionStorage so the user can navigate between
// /materials, /onboarding, and /chat without losing their picks.
//
// Critical invariant: a stored ID is only meaningful if the BE still has the
// corresponding material. After server restarts or cross-tab deletes, stored
// IDs can become orphans. Anywhere we display or use these IDs, we must first
// `reconcileSelectedMaterials()` to drop the dead ones.

import { listMaterials } from "@/lib/api";

const SELECTED_KEY = "tq:selected_materials";

export function getSelectedMaterialIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(SELECTED_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

export function setSelectedMaterialIds(ids: string[]): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(SELECTED_KEY, JSON.stringify(ids));
}

/** Fetch the live material list from BE and prune any stored selection IDs
 *  that don't correspond to an existing material. Returns the cleaned ID
 *  array. Throws if BE is unreachable — caller decides how to recover. */
export async function reconcileSelectedMaterials(): Promise<string[]> {
  const stored = getSelectedMaterialIds();
  if (stored.length === 0) return [];
  const live = await listMaterials();
  const liveIds = new Set(live.map((m) => m.id));
  const pruned = stored.filter((id) => liveIds.has(id));
  if (pruned.length !== stored.length) {
    setSelectedMaterialIds(pruned);
  }
  return pruned;
}
