// docs/spec/API.md §2.2 Source 와 §3.2 출처 렌더 규칙(frontEndSpec.md)의 단일 진실 소스.

export type SourceType =
  | "notice"
  | "notice_pdf"
  | "mentoring"
  | "application"
  | "webex_message"
  | "webex_summary"
  | "calendar"
  | "other";

export type Source = {
  id?: string;
  type: SourceType;
  title: string;
  url?: string;
  createdAt?: string; // ISO 8601
  collectedAt?: string; // ISO 8601
  official: boolean; // OpenSoma=true, Webex=false
  rawRef?: string;
};

export const SOURCE_TYPE_LABEL: Record<SourceType, string> = {
  notice: "공지",
  notice_pdf: "공지 PDF",
  mentoring: "멘토링",
  application: "접수 내역",
  webex_message: "Webex 메시지",
  webex_summary: "Webex 요약",
  calendar: "캘린더",
  other: "참고 자료",
};
