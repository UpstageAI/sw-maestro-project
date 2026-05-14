"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { fetchSyncInfo, type SyncInfoResponse } from "@/lib/syncInfo";

type Status = "idle" | "loading" | "success" | "error";

export type UseSyncInfoState = {
  data: SyncInfoResponse | null;
  status: Status;
  error: string | null;
  lastFetchedAt: Date | null;
  refresh: () => void;
};

const DEFAULT_INTERVAL_MS = 60_000;

export function useSyncInfo(
  intervalMs: number = DEFAULT_INTERVAL_MS,
): UseSyncInfoState {
  const [data, setData] = useState<SyncInfoResponse | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);

  // refresh()가 effect 내부 trigger 함수를 호출하기 위한 통로.
  const triggerRef = useRef<() => void>(() => {});

  useEffect(() => {
    let cancelled = false;
    let abortController: AbortController | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const runOnce = async () => {
      abortController?.abort();
      const controller = new AbortController();
      abortController = controller;

      setStatus((prev) => (prev === "success" ? "success" : "loading"));

      try {
        const next = await fetchSyncInfo(controller.signal);
        if (cancelled || controller.signal.aborted) return;
        setData(next);
        setStatus("success");
        setError(null);
        setLastFetchedAt(new Date());
      } catch (cause) {
        if (cancelled || controller.signal.aborted) return;

        const message =
          cause instanceof ApiError
            ? cause.message
            : cause instanceof Error
              ? cause.message
              : "알 수 없는 오류";
        setStatus("error");
        setError(message);
        setLastFetchedAt(new Date());
      }
    };

    const tick = async () => {
      if (cancelled) return;
      // 백그라운드 탭이면 한 주기 미루고 다시 예약.
      if (
        typeof document !== "undefined" &&
        document.visibilityState === "hidden"
      ) {
        timer = setTimeout(tick, intervalMs);
        return;
      }
      await runOnce();
      if (!cancelled) timer = setTimeout(tick, intervalMs);
    };

    triggerRef.current = () => {
      if (cancelled) return;
      if (timer) clearTimeout(timer);
      void tick();
    };

    void tick();

    const onVisibility = () => {
      if (cancelled) return;
      if (document.visibilityState === "visible") {
        if (timer) clearTimeout(timer);
        void tick();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      abortController?.abort();
      if (timer) clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibility);
      triggerRef.current = () => {};
    };
  }, [intervalMs]);

  const refresh = useCallback(() => {
    triggerRef.current();
  }, []);

  return { data, status, error, lastFetchedAt, refresh };
}
