import { create } from 'zustand';
import type { PipelineResultDto, RecommendResult, UserInput } from '../types';

interface TravelStore {
  userInput: UserInput | null;
  result: RecommendResult | null;
  pipelineResult: PipelineResultDto | null;
  setUserInput: (input: UserInput) => void;
  setResult: (result: RecommendResult) => void;
  setPipelineResult: (result: PipelineResultDto) => void;
  /** Wipe everything — used by "처음으로". */
  reset: () => void;
  /** Wipe only the analysis result + cached pipeline output, keep userInput. */
  resetResultOnly: () => void;
}

export const useTravelStore = create<TravelStore>((set) => ({
  userInput: null,
  result: null,
  pipelineResult: null,
  setUserInput: (input) => set({ userInput: input }),
  setResult: (result) => set({ result }),
  setPipelineResult: (pipelineResult) => set({ pipelineResult }),
  reset: () => set({ userInput: null, result: null, pipelineResult: null }),
  resetResultOnly: () => set({ result: null, pipelineResult: null }),
}));
