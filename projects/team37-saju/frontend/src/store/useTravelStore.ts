import { create } from 'zustand';
import type { UserInput, RecommendResult } from '../types';

interface TravelStore {
  userInput: UserInput | null;
  result: RecommendResult | null;
  setUserInput: (input: UserInput) => void;
  setResult: (result: RecommendResult) => void;
  reset: () => void;
}

export const useTravelStore = create<TravelStore>((set) => ({
  userInput: null,
  result: null,
  setUserInput: (input) => set({ userInput: input }),
  setResult: (result) => set({ result }),
  reset: () => set({ userInput: null, result: null }),
}));
