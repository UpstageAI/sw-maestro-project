// docs/spec/API.md §2.2 ChatUIBlock.notice_list 의 items 타입.
// 정확한 필드는 sidecar PoC 후 확정 (frontEndSpec §7 F-1).
// frontEndSpec §3.2 — "내 접수 내역 보여줘"가 notice_list 형태로 재사용될 수도 있음 (F-2).
// 본 파일은 시연용 잠정 컨트랙트이며, 백엔드 확정 시 본 파일 + mockChat 만 갱신하면 된다.

export type NoticeAttachmentType =
  | "pdf"
  | "image"
  | "doc"
  | "link"
  | "other";

export type NoticeAttachment = {
  id?: string;
  type: NoticeAttachmentType;
  name: string;
  url?: string;
  sizeBytes?: number;
};

export type NoticeCategory =
  | "운영"
  | "평가"
  | "워크숍"
  | "시스템"
  | "기타";

export type NoticeCard = {
  id: string;
  title: string;
  author: string;
  createdAt: string; // ISO 8601
  url?: string; // 원본 공지 링크 (OpenSoma)
  summary?: string;
  category?: NoticeCategory;
  pinned?: boolean; // 필독 여부
  unread?: boolean; // 사용자 기준 미열람 여부
  attachments?: NoticeAttachment[];
};

export function formatFileSize(bytes?: number): string | null {
  if (!bytes || bytes <= 0) return null;
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  const rounded = value >= 10 || idx === 0 ? Math.round(value) : value.toFixed(1);
  return `${rounded} ${units[idx]}`;
}

export function sortNotices(items: NoticeCard[]): NoticeCard[] {
  return [...items].sort((a, b) => {
    if ((b.pinned ? 1 : 0) !== (a.pinned ? 1 : 0)) {
      return (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0);
    }
    return (
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  });
}
