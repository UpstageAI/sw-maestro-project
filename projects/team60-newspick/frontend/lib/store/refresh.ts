import { create } from "zustand";

export const REFRESH_STEP_NAMES = [
  "collect",
  "summarize",
  "prepare",
] as const;

export type RefreshStepName = (typeof REFRESH_STEP_NAMES)[number];
type RefreshStatus = "idle" | "loading" | "done" | "error";

type RefreshStep = {
  current: number;
  total: number;
};

type RefreshState = {
  collect: RefreshStep;
  summarize: RefreshStep;
  prepare: RefreshStep;
  errorMessage: string | null;
  finalizing: boolean;
  status: RefreshStatus;
  setStep: (step: RefreshStepName, current: number, total: number) => void;
  setErrorMessage: (message: string | null) => void;
  setFinalizing: (finalizing: boolean) => void;
  setStatus: (status: RefreshStatus) => void;
  reset: () => void;
};

const initialState = {
  collect: { current: 0, total: 0 },
  summarize: { current: 0, total: 0 },
  prepare: { current: 0, total: 0 },
  errorMessage: null,
  finalizing: false,
  status: "idle" as RefreshStatus,
};

export function isRefreshStepName(step: string | undefined): step is RefreshStepName {
  return REFRESH_STEP_NAMES.includes(step as RefreshStepName);
}

export const useRefreshStore = create<RefreshState>((set) => ({
  ...initialState,
  setStep: (step, current, total) =>
    set({
      [step]: {
        current,
        total,
      },
    }),
  setErrorMessage: (message) => set({ errorMessage: message }),
  setFinalizing: (finalizing) => set({ finalizing }),
  setStatus: (status) => set({ status }),
  reset: () => set(initialState),
}));
