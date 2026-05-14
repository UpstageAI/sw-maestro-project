import { apiFetch } from "@/lib/api";
import type { KnowledgeAskRequest, KnowledgeAskResponse } from "@/lib/types/knowledge";

export async function askKnowledge(
  body: KnowledgeAskRequest,
  signal?: AbortSignal,
): Promise<KnowledgeAskResponse> {
  return apiFetch<KnowledgeAskResponse>("/api/v1/knowledge/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
    signal,
  });
}
