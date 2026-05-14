import { Redis } from "@upstash/redis";
import type { JobRecord } from "./types";

// Vercel KV (Upstash) auto-injects KV_REST_API_URL/TOKEN when the integration
// is connected to the project. UPSTASH_REDIS_REST_* variants are also accepted
// for direct Upstash setups. When neither is configured (e.g. remote dev),
// fall back to an in-memory Map keyed on globalThis.
const KV_URL =
  process.env.KV_REST_API_URL ?? process.env.UPSTASH_REDIS_REST_URL;
const KV_TOKEN =
  process.env.KV_REST_API_TOKEN ?? process.env.UPSTASH_REDIS_REST_TOKEN;
const useKv = Boolean(KV_URL && KV_TOKEN);

const TTL_SECONDS = 60 * 60; // jobs expire 1 hour after last write

let redisClient: Redis | null = null;
function redis(): Redis {
  if (!redisClient) {
    redisClient = new Redis({ url: KV_URL!, token: KV_TOKEN! });
  }
  return redisClient;
}

const globalForStore = globalThis as typeof globalThis & {
  promotionJobStore?: Map<string, JobRecord>;
};
const memStore =
  globalForStore.promotionJobStore ?? new Map<string, JobRecord>();
if (!globalForStore.promotionJobStore) {
  globalForStore.promotionJobStore = memStore;
}

function jobKey(id: string): string {
  return `promotion:job:${id}`;
}

export async function getJob(id: string): Promise<JobRecord | null> {
  if (useKv) {
    return (await redis().get<JobRecord>(jobKey(id))) ?? null;
  }
  return memStore.get(id) ?? null;
}

export async function setJob(record: JobRecord): Promise<void> {
  const next: JobRecord = {
    ...record,
    updatedAt: new Date().toISOString(),
  };
  if (useKv) {
    await redis().set(jobKey(record.id), next, { ex: TTL_SECONDS });
    return;
  }
  memStore.set(record.id, next);
}

export async function patchJob(
  id: string,
  patch: Partial<JobRecord>,
): Promise<JobRecord | null> {
  const current = await getJob(id);
  if (!current) return null;
  const next: JobRecord = {
    ...current,
    ...patch,
    updatedAt: new Date().toISOString(),
  };
  if (useKv) {
    await redis().set(jobKey(id), next, { ex: TTL_SECONDS });
  } else {
    memStore.set(id, next);
  }
  return next;
}
