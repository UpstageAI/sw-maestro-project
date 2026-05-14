import type { KnowledgeSource } from "@/lib/types/knowledge";
import type { Source, SourceType } from "@/lib/types/source";

const SOURCE_TYPE_MAP: Record<
  KnowledgeSource["source_type"],
  SourceType
> = {
  NOTICE: "notice",
  NOTICE_PDF: "notice_pdf",
  MENTORING: "mentoring",
  WEBEX_MESSAGE: "webex_message",
};

export function knowledgeSourcesToUiSources(
  items: KnowledgeSource[],
): Source[] {
  return items.map((item, index) => {
    const id = `${item.chunk_id}-${item.source_id}-${index}`;
    return {
      id,
      type: SOURCE_TYPE_MAP[item.source_type] ?? "other",
      title: item.title,
      url: item.source_url ?? undefined,
      createdAt: item.created_at ?? undefined,
      official: item.official,
      rawRef:
        !item.source_url && item.text
          ? item.text.length > 200
            ? `${item.text.slice(0, 200)}…`
            : item.text
          : item.room_name
            ? `room: ${item.room_name}`
            : undefined,
    };
  });
}
