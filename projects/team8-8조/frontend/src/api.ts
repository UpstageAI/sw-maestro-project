import type { AppSettings, BriefingResult, CollectionResult } from './types';

const BASE = '/api';

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? '요청 실패');
  }
  return res.json();
}

export async function fetchSettings(): Promise<AppSettings> {
  const res = await fetch(`${BASE}/settings`);
  if (!res.ok) throw new Error('설정 조회 실패');
  return res.json();
}

export async function collectNews(
  interest: string,
  keyword_text: string,
  per_keyword_limit: number,
): Promise<CollectionResult> {
  return post('/collect', { interest, keyword_text, per_keyword_limit });
}

export async function generateBriefing(
  collection: CollectionResult,
  top_k: number,
): Promise<BriefingResult> {
  return post('/briefing', {
    interest: collection.interest,
    keywords: collection.keywords,
    top_k,
    collected_articles: collection.collected_articles,
    collected_count: collection.collected_count,
    stored_count: collection.stored_count,
    skipped_existing_count: collection.skipped_existing_count,
    errors: collection.errors,
  });
}

export async function sendEmail(
  recipient: string,
  briefing_result: BriefingResult,
): Promise<void> {
  await post('/send-email', { recipient, briefing_result });
}
