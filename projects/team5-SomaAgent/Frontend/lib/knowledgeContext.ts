import type { ThreadMessage } from "@/lib/knowledgeChat";

const MAX_PRIOR_TURNS = 3;
const MAX_ASSISTANT_SNIPPET = 600;
const MAX_USER_SNIPPET = 400;

/** knowledge/ask에 `candidates_context` 필드가 없어, 이전 턴을 질문 문자열에 포함한다. */
export function buildKnowledgeQueryWithContext(
  priorMessages: ThreadMessage[],
  currentUserText: string,
): string {
  const relevant = priorMessages.filter(
    (m) => m.role === "user" || (m.role === "assistant" && m.kind === "knowledge"),
  );

  const tail = relevant.slice(-MAX_PRIOR_TURNS * 2);

  if (tail.length === 0) return currentUserText.trim();

  const lines: string[] = [
    "[이전 대화 맥락 — 동일 주제 후속 질문일 수 있음]",
  ];

  for (const m of tail) {
    if (m.role === "user") {
      const t = m.text.length > MAX_USER_SNIPPET
        ? `${m.text.slice(0, MAX_USER_SNIPPET)}…`
        : m.text;
      lines.push(`사용자: ${t}`);
    } else if (m.role === "assistant" && m.kind === "knowledge") {
      let a = m.answer.trim();
      if (a.length > MAX_ASSISTANT_SNIPPET) {
        a = `${a.slice(0, MAX_ASSISTANT_SNIPPET)}…`;
      }
      lines.push(`어시스턴트: ${a}`);
      if (m.sources.length > 0) {
        const titles = m.sources
          .slice(0, 5)
          .map((s) => `${s.source_type}:${s.title}`)
          .join("; ");
        lines.push(`(참고 출처 일부: ${titles})`);
      }
    }
  }

  lines.push("");
  lines.push(`[현재 질문]\n${currentUserText.trim()}`);

  return lines.join("\n");
}
