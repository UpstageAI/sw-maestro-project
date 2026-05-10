import { browser } from '$app/environment';
import { CHAT_STATE_VERSION, type ChatState, type Language, type Mission, type Verdict } from './types';

const KEY_LANG = 'duribeon:language';
const KEY_JOURNAL = 'duribeon:journal';
const KEY_CHAT = 'duribeon:chat';
const MAX_JOURNAL = 30;
const MAX_CHAT_MESSAGES = 120;

export interface JournalEntry {
  ts: number;
  language: Language;
  mission: Mission;
  verdict: Verdict;
  thumbnail?: string;
}

function read<T>(key: string, fallback: T): T {
  if (!browser) return fallback;
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  if (!browser) return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* quota — silent */
  }
}

function remove(key: string) {
  if (!browser) return;
  localStorage.removeItem(key);
}

export function loadLanguage(): Language {
  const v = read<string>(KEY_LANG, 'ko');
  return v === 'en' ? 'en' : 'ko';
}
export function saveLanguage(lang: Language) {
  write(KEY_LANG, lang);
}

export function loadJournal(): JournalEntry[] {
  const list = read<JournalEntry[]>(KEY_JOURNAL, []);
  return Array.isArray(list) ? list : [];
}
export function appendJournal(entry: JournalEntry) {
  const cur = loadJournal();
  cur.unshift(entry);
  if (cur.length > MAX_JOURNAL) cur.length = MAX_JOURNAL;
  write(KEY_JOURNAL, cur);
}
export function clearJournal() {
  remove(KEY_JOURNAL);
}

export function loadChat(): ChatState | null {
  const state = read<ChatState | null>(KEY_CHAT, null);
  if (!state || state.version !== CHAT_STATE_VERSION) {
    if (state) remove(KEY_CHAT);
    return null;
  }
  return state;
}
export function saveChat(state: ChatState) {
  const trimmed: ChatState = {
    ...state,
    version: CHAT_STATE_VERSION,
    messages: state.messages.slice(-MAX_CHAT_MESSAGES)
  };
  write(KEY_CHAT, trimmed);
}
export function clearChat() {
  remove(KEY_CHAT);
}

export async function fileToThumbnail(file: File, max = 320): Promise<string> {
  const bitmap = await createImageBitmap(file);
  const ratio = Math.min(max / bitmap.width, max / bitmap.height, 1);
  const w = Math.max(1, Math.round(bitmap.width * ratio));
  const h = Math.max(1, Math.round(bitmap.height * ratio));

  let blob: Blob;
  if (typeof OffscreenCanvas !== 'undefined') {
    const canvas = new OffscreenCanvas(w, h);
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('canvas 2d context unavailable');
    ctx.drawImage(bitmap, 0, 0, w, h);
    blob = await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.7 });
  } else {
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('canvas 2d context unavailable');
    ctx.drawImage(bitmap, 0, 0, w, h);
    blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (b) => (b ? resolve(b) : reject(new Error('toBlob failed'))),
        'image/jpeg',
        0.7
      );
    });
  }

  return await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

export function formatTimestamp(ts: number, lang: Language): string {
  const d = new Date(ts);
  const locale = lang === 'ko' ? 'ko-KR' : 'en-US';
  return d.toLocaleString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function shortTime(ts: number, lang: Language): string {
  const d = new Date(ts);
  const locale = lang === 'ko' ? 'ko-KR' : 'en-US';
  return d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
}
