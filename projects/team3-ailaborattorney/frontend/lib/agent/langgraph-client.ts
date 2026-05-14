import type { AnalyzeRequest, AnalyzeResponse, QaRequest, QaResponse } from "./types";

const TIMEOUT_MS = 15000;

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${txt}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(t);
  }
}

export async function analyzeWithLangGraph(baseUrl: string, req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const data = await postJson<Omit<AnalyzeResponse, "source">>(`${baseUrl.replace(/\/$/, "")}/analyze`, req);
  return { ...data, source: "langgraph" };
}

export async function qaWithLangGraph(baseUrl: string, req: QaRequest): Promise<QaResponse> {
  const data = await postJson<Omit<QaResponse, "source">>(`${baseUrl.replace(/\/$/, "")}/qa`, req);
  return { ...data, source: "langgraph" };
}
