import type { KnowledgeSource } from "@/lib/types/knowledge";
import type { MentoringCard } from "@/lib/types/mentoring";

/** 카드 id가 OpenAPI path의 정수 mentoring_id로 파싱 가능한지 */
export function isNumericMentoringId(id: string): boolean {
  return /^\d+$/.test(id.trim());
}

/**
 * RAG 청크 본문에 접수·마감 상태가 섞여 있을 때, "접수 중"류 문구가 있으면 해당 청크를 신청 가능으로 봅니다.
 * 마감만 적힌 회차는 신청 카드 목록에 넣지 않습니다.
 */
export function isMentoringChunkOpenForApply(s: KnowledgeSource): boolean {
  const blob = `${s.title}\n${s.text}`.replace(/\s+/g, " ");

  const hasOpen =
    /접수\s*중|접수중|접수\s*가능|모집\s*중/.test(blob);

  const hasClosed =
    /마감\s*20\d{2}[-./]\d{1,2}[-./]\d{1,2}/.test(blob) ||
    /마감\s*20\d{2}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일/.test(blob) ||
    /\b마감\s*\d{1,2}\s*월\s*\d{1,2}\s*일\b/.test(blob) ||
    /(?:신청|모집|접수)\s*마감|모집\s*종료|마감\s*되었/.test(blob);

  if (hasOpen) return true;
  if (hasClosed) return false;
  return false;
}

function dedupeMentoringSourcesById(sources: KnowledgeSource[]): KnowledgeSource[] {
  const seen = new Set<string>();
  const out: KnowledgeSource[] = [];
  for (const s of sources) {
    const id = String(s.source_id).trim();
    if (seen.has(id)) continue;
    seen.add(id);
    out.push(s);
  }
  return out;
}

export function knowledgeMentoringSourcesToCards(
  sources: KnowledgeSource[],
): MentoringCard[] {
  const ready = dedupeMentoringSourcesById(
    sources
      .filter((s) => s.source_type === "MENTORING")
      .filter((s) => isNumericMentoringId(String(s.source_id)))
      .filter(isMentoringChunkOpenForApply),
  );

  return ready.map((s) => {
    const id = String(s.source_id).trim();
    return {
      id,
      title: s.title,
      mentor: {
        name: s.room_name?.trim() || "멘토링",
      },
      tags: [],
      description:
        s.text.length > 800 ? `${s.text.slice(0, 800)}…` : s.text,
      sessionStartedAt: s.created_at ?? new Date().toISOString(),
      status: "open" as const,
    };
  });
}
