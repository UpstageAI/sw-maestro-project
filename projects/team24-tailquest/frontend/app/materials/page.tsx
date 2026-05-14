"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Icon } from "@/components/chrome/icon";
import { MaterialList } from "@/components/materials/material-list";
import { UploadCard } from "@/components/materials/upload-card";

import {
  deleteMaterial,
  getMaterial,
  ingestGithub,
  listMaterials,
  uploadMaterial,
  type MaterialResponse,
} from "@/lib/api";
import {
  getSelectedMaterialIds,
  setSelectedMaterialIds,
} from "@/lib/materials-selection";

const POLL_INTERVAL_MS = 5000;

function readSelectedIds(): Set<string> {
  return new Set(getSelectedMaterialIds());
}

function persistSelectedIds(ids: Set<string>) {
  setSelectedMaterialIds([...ids]);
}

export default function MaterialsPage() {
  const router = useRouter();
  const [items, setItems] = useState<MaterialResponse[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  // Latches once "면접 시작" is clicked so a rapid second click can't double-route.
  const [starting, setStarting] = useState(false);
  const pollingRefs = useRef<Map<string, ReturnType<typeof setInterval>>>(
    new Map(),
  );

  // Load initial list + restore selection from sessionStorage.
  // After fetching the live list, prune any stored selection IDs whose
  // material no longer exists (stale references from prior sessions).
  useEffect(() => {
    const stored = readSelectedIds();
    setSelectedIds(stored);
    listMaterials()
      .then((data) => {
        setItems(data);
        // Prune the stored selection on two axes:
        //  1. ids whose row no longer exists in the live list
        //  2. ids whose row exists but isn't ready (indexing or failed) —
        //     selection should only contain attachable materials, otherwise
        //     /chat would hand a no-op material_id to the graph.
        const readyLiveIds = new Set(
          data.filter((m) => m.status === "ready").map((m) => m.id),
        );
        const pruned = new Set([...stored].filter((id) => readyLiveIds.has(id)));
        if (pruned.size !== stored.size) {
          persistSelectedIds(pruned);
          setSelectedIds(pruned);
        }
        data
          .filter((m) => m.status === "indexing")
          .forEach((m) => startPolling(m.id));
      })
      .catch(() => {
        // Backend offline — show empty state, no crash.
      });

    return () => {
      // Cleanup all polling intervals on unmount.
      pollingRefs.current.forEach((timer) => clearInterval(timer));
      pollingRefs.current.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startPolling = useCallback((id: string) => {
    if (pollingRefs.current.has(id)) return;
    const timer = setInterval(async () => {
      try {
        const updated = await getMaterial(id);
        setItems((prev) =>
          prev.map((m) => (m.id === id ? updated : m)),
        );
        if (updated.status !== "indexing") {
          clearInterval(pollingRefs.current.get(id));
          pollingRefs.current.delete(id);
          // If the material ended up failed, drop it from the active
          // selection so /chat doesn't hand a phantom material_id to the
          // graph (Chroma has no chunks for a failed ingest).
          if (updated.status === "failed") {
            setSelectedIds((prev) => {
              if (!prev.has(id)) return prev;
              const next = new Set(prev);
              next.delete(id);
              persistSelectedIds(next);
              return next;
            });
          }
        }
      } catch {
        // Ignore transient poll errors.
      }
    }, POLL_INTERVAL_MS);
    pollingRefs.current.set(id, timer);
  }, []);

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadMaterial(file);
      setItems((prev) => [result, ...prev]);
      if (result.status === "indexing") startPolling(result.id);
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "업로드에 실패했습니다.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleGithub(url: string) {
    setUploading(true);
    setUploadError(null);
    try {
      const result = await ingestGithub(url);
      setItems((prev) => [result, ...prev]);
      // GitHub always starts as "indexing".
      startPolling(result.id);
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "GitHub 인입에 실패했습니다.",
      );
    } finally {
      setUploading(false);
    }
  }

  function handleToggle(id: string) {
    // Defense in depth — MaterialCard already disables the checkbox when not
    // ready, but if some race fires a toggle event anyway, refuse it here.
    const item = items.find((m) => m.id === id);
    if (item && item.status !== "ready" && !selectedIds.has(id)) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      persistSelectedIds(next);
      return next;
    });
  }

  async function handleDelete(id: string) {
    try {
      await deleteMaterial(id);
      setItems((prev) => prev.filter((m) => m.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        persistSelectedIds(next);
        return next;
      });
      // Stop polling if it was running.
      if (pollingRefs.current.has(id)) {
        clearInterval(pollingRefs.current.get(id));
        pollingRefs.current.delete(id);
      }
    } catch (err) {
      // Surface delete failures in the upload error area.
      setUploadError(
        err instanceof Error ? err.message : "삭제에 실패했습니다.",
      );
    }
  }

  function startInterview() {
    if (starting) return;
    setStarting(true);
    // Persist selection to sessionStorage so chat-shell can read it.
    persistSelectedIds(selectedIds);
    router.push("/chat");
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-canvas">
      {/* Header */}
      <header className="shrink-0 border-b border-hairline bg-canvas">
        <div className="max-w-airbnb mx-auto px-xl py-md flex items-center justify-between gap-md">
          <h1 className="text-display-sm text-ink">자료 관리</h1>
          <Link
            href="/onboarding"
            className="text-button-sm text-muted hover:text-ink underline underline-offset-4 transition-colors"
          >
            ← 온보딩으로 돌아가기
          </Link>
        </div>
      </header>

      {/* Main — two-column on large screens */}
      <main className="flex-1 min-h-0 overflow-hidden">
        <div className="max-w-airbnb mx-auto h-full px-xl py-lg flex flex-col lg:flex-row gap-lg min-h-0">
          {/* Left — Upload (40%) */}
          <div className="lg:w-[40%] shrink-0 flex flex-col gap-md">
            <h2 className="text-title-md text-ink">자료 추가</h2>
            <UploadCard
              onUpload={handleUpload}
              onGithub={handleGithub}
              loading={uploading}
            />
            {uploadError && (
              <p className="text-body-sm text-error-text rounded-md border border-rausch bg-rausch/5 p-md">
                {uploadError}
              </p>
            )}
            <p className="text-caption-sm text-muted">
              업로드한 자료는 면접 세션의 꼬리 질문 생성에 활용됩니다. 자료 없이 시작하면 공개 자료만 사용합니다.
            </p>
          </div>

          {/* Right — Material list (60%) */}
          <div className="flex-1 min-h-0 flex flex-col gap-md overflow-hidden">
            <div className="flex items-center justify-between shrink-0">
              <h2 className="text-title-md text-ink">
                등록된 자료
                {items.length > 0 && (
                  <span className="ml-sm text-caption-sm text-muted font-normal">
                    {items.length}건
                  </span>
                )}
              </h2>
              {selectedIds.size > 0 && (
                <span className="text-body-sm text-muted">
                  {selectedIds.size}개 선택됨
                </span>
              )}
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin pr-sm" style={{ scrollbarGutter: "stable" }}>
              <MaterialList
                items={items}
                selectedIds={selectedIds}
                onToggle={handleToggle}
                onDelete={handleDelete}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Action bar */}
      <footer className="shrink-0 border-t border-hairline bg-canvas">
        <div className="max-w-airbnb mx-auto px-xl py-md flex items-center justify-between gap-md">
          <p className="text-body-sm text-muted">
            {selectedIds.size > 0
              ? `선택한 자료 ${selectedIds.size}개로 면접에 활용됩니다.`
              : "자료를 선택하지 않으면 공개 자료만 사용합니다."}
          </p>
          <button
            type="button"
            onClick={startInterview}
            disabled={starting}
            className="btn-primary flex items-center gap-sm"
          >
            <Icon name="play_arrow" size={18} filled />
            {starting
              ? "시작 중…"
              : selectedIds.size > 0
                ? `선택한 자료로 면접 시작`
                : "면접 시작"}
          </button>
        </div>
      </footer>
    </div>
  );
}
