// docs/spec/API.md §2.2 ChatUIBlock.mentoring_cards 의 items 타입.
// 정확한 필드는 sidecar PoC 후 확정 (frontEndSpec §7 F-1).
// 본 파일은 시연용 잠정 컨트랙트이며, 백엔드 확정 시 본 파일 + mockChat 만 갱신하면 된다.

export type MentoringStatus = "open" | "applied" | "closed";

export type MentoringMentor = {
  name: string;
  organization?: string;
  photoUrl?: string;
};

export type MentoringLocation =
  | { type: "online" }
  | { type: "offline"; place: string };

export type MentoringCapacity = {
  current: number;
  max: number;
};

export type MentoringCard = {
  id: string; // mentoringId
  title: string;
  mentor: MentoringMentor;
  tags: string[];
  description?: string;
  sessionStartedAt: string; // ISO 8601
  sessionEndedAt?: string; // ISO 8601
  location?: MentoringLocation;
  capacity?: MentoringCapacity;
  status: MentoringStatus;
  applySn?: number; // status === "applied" 일 때 동봉
  qustnrSn?: number; // status === "applied" 일 때 동봉
};

export function isCapacityFull(card: MentoringCard): boolean {
  if (!card.capacity) return false;
  return card.capacity.current >= card.capacity.max;
}

export function getCapacityRatio(card: MentoringCard): number {
  if (!card.capacity || card.capacity.max <= 0) return 0;
  return Math.min(1, card.capacity.current / card.capacity.max);
}
