import type { ActionResult } from "@/lib/types/action";
import type { KnowledgeSource } from "@/lib/types/knowledge";

/** `/chat` RAG(knowledge/ask) 스레드에 표시되는 메시지. */
export type ThreadMessage =
  | { id: string; role: "user"; text: string }
  | {
      id: string;
      role: "assistant";
      kind: "knowledge";
      answer: string;
      sources: KnowledgeSource[];
      llm_used: boolean;
      llm_error?: string | null;
    }
  | { id: string; role: "assistant"; kind: "error"; message: string }
  | {
      id: string;
      role: "agent";
      kind: "action_result";
      results: ActionResult[];
    };
