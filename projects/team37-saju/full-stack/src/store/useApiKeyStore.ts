import { create } from 'zustand';

const STORAGE_KEY = 'saju-travel:solar-api-key';

function readInitial(): string {
  if (typeof window === 'undefined') return '';
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) ?? '';
  } catch {
    return '';
  }
}

interface ApiKeyStore {
  apiKey: string;
  setApiKey: (key: string) => void;
  clearApiKey: () => void;
}

export const useApiKeyStore = create<ApiKeyStore>((set) => ({
  apiKey: readInitial(),
  setApiKey: (key) => {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, key);
    } catch {
      /* ignore quota errors */
    }
    set({ apiKey: key });
  },
  clearApiKey: () => {
    try {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    set({ apiKey: '' });
  },
}));
