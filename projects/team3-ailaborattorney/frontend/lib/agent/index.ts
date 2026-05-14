import type { AnalyzeRequest, AnalyzeResponse, QaRequest, QaResponse } from "./types";
import { analyzeWithLangGraph, qaWithLangGraph } from "./langgraph-client";
import { analyzeMock, qaMock } from "./mock";

export * from "./types";

function baseUrl(): string | null {
  const u = process.env.LANGGRAPH_URL?.trim();
  return u && u.length > 0 ? u : null;
}

export async function analyze(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const url = baseUrl();
  if (!url) return analyzeMock(req);
  try { return await analyzeWithLangGraph(url, req); }
  catch (e) {
    console.warn("[agent] LangGraph 실패, mock fallback:", (e as Error).message);
    return analyzeMock(req);
  }
}

export async function qa(req: QaRequest): Promise<QaResponse> {
  const url = baseUrl();
  if (!url) return qaMock(req);
  try { return await qaWithLangGraph(url, req); }
  catch (e) {
    console.warn("[agent] LangGraph 실패, mock fallback:", (e as Error).message);
    return qaMock(req);
  }
}
