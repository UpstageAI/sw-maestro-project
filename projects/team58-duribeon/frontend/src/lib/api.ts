import type { AreaInfo, ContextInput, Language, Mission, Verdict } from './types';

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

const DEFAULT_TIMEOUT_MS = 60_000;

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

async function fetchWithTimeout(
  input: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchAreas(): Promise<AreaInfo[]> {
  const res = await fetchWithTimeout(`${BASE}/api/areas`, {}, 10_000);
  const data = await handle<{ areas: AreaInfo[] }>(res);
  return data.areas;
}

export async function detectLanguage(text: string): Promise<Language> {
  const res = await fetchWithTimeout(
    `${BASE}/api/lang/detect`,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text })
    },
    10_000
  );
  const data = await handle<{ language: Language }>(res);
  return data.language;
}

export async function regenerateMission(
  ctx: ContextInput,
  placeId: string,
  previousTitle?: string
): Promise<Mission> {
  const res = await fetchWithTimeout(`${BASE}/api/missions/regenerate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      area: ctx.area,
      group: ctx.group,
      time_budget: ctx.timeBudget,
      mood: ctx.mood,
      avoid: ctx.avoid,
      language: ctx.language,
      place_id: placeId,
      previous_title: previousTitle ?? null
    })
  });
  const data = await handle<{ mission: Mission }>(res);
  return data.mission;
}

export async function generateMissions(
  ctx: ContextInput,
  rejectedPlaceIds: string[]
): Promise<Mission[]> {
  const res = await fetchWithTimeout(`${BASE}/api/missions/generate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      area: ctx.area,
      group: ctx.group,
      time_budget: ctx.timeBudget,
      mood: ctx.mood,
      avoid: ctx.avoid,
      language: ctx.language,
      rejected_place_ids: rejectedPlaceIds
    })
  });
  const data = await handle<{ missions: Mission[] }>(res);
  return data.missions;
}

export async function verifyPhoto(
  photo: File,
  mission: Mission,
  language: Language
): Promise<Verdict> {
  const fd = new FormData();
  fd.append('photo', photo);
  fd.append('mission_json', JSON.stringify(mission));
  fd.append('language', language);
  const res = await fetchWithTimeout(`${BASE}/api/missions/verify`, {
    method: 'POST',
    body: fd
  });
  return handle<Verdict>(res);
}
