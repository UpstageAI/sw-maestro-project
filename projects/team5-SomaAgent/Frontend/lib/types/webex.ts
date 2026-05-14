// docs/spec/API.md §2.2 ChatUIBlock.webex_summary 의 items 타입.
// `WebexSummaryItem` 정확한 필드는 sidecar PoC 후 확정 (frontEndSpec §7 F-1).
// 본 파일은 시연용 잠정 컨트랙트이며, 백엔드 확정 시 본 파일 + mockChat 만 갱신하면 된다.

export type WebexHighlight = {
  id?: string;
  author: string;
  text: string;
  createdAt?: string; // ISO 8601
};

export type WebexSummaryItem = {
  id: string;
  roomId: string;
  roomName: string;
  topic: string; // 클러스터/주제 제목 (LLM 요약)
  summary: string; // 본문 요약 (한국어)
  messageCount: number;
  participants: string[];
  startedAt?: string; // ISO 8601
  endedAt?: string; // ISO 8601
  highlights?: WebexHighlight[]; // 대표 메시지(원문 일부)
  rawRefs?: string[]; // 원본 메시지 URI 목록
};

export type WebexRoomGroup = {
  roomId: string;
  roomName: string;
  items: WebexSummaryItem[];
};

export function groupWebexByRoom(
  items: WebexSummaryItem[],
): WebexRoomGroup[] {
  const order: string[] = [];
  const buckets = new Map<string, WebexRoomGroup>();

  for (const item of items) {
    const existing = buckets.get(item.roomId);
    if (existing) {
      existing.items.push(item);
      continue;
    }
    order.push(item.roomId);
    buckets.set(item.roomId, {
      roomId: item.roomId,
      roomName: item.roomName,
      items: [item],
    });
  }

  return order.map((roomId) => buckets.get(roomId)!);
}
