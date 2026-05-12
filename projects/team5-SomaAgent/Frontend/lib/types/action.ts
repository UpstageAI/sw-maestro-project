// docs/spec/API.md §3.1 ActionExecutionResponse 와 §2.2 ChatUIBlock.action_result 의
// 단일 진실 소스. 백엔드 변경 시 본 파일도 함께 갱신.

export type ActionType = "MENTORING_APPLY" | "MENTORING_CANCEL";

export type ApplicationData = {
  applySn: number;
  qustnrSn: number;
  mentoringId: string;
  title: string;
  sessionStartedAt?: string; // ISO 8601
};

export type CalendarInviteStatus = "created" | "skipped" | "failed";

export type CalendarInviteData = {
  status: CalendarInviteStatus;
  eventId?: string;
  errorMessage?: string;
};

export type ActionExecutionError = {
  code: string;
  message: string;
  recoverable: boolean;
};

// /api/v1/actions/execute 응답 ≒ ChatUIBlock.action_result.results[i]
export type ActionResult = {
  actionType: ActionType;
  status: "success" | "failed";
  message: string;
  data?: {
    application?: ApplicationData;
    calendarInvite?: CalendarInviteData;
  };
  error?: ActionExecutionError;
  traceId?: string;
};

// 화면 렌더용 파생 톤. 캘린더 실패는 "부분 실패"로 강등.
export type ActionResultTone = "success" | "partial" | "failed";

export function deriveActionResultTone(result: ActionResult): ActionResultTone {
  if (result.status === "failed") return "failed";
  if (result.data?.calendarInvite?.status === "failed") return "partial";
  return "success";
}

export const ACTION_TYPE_LABEL: Record<ActionType, string> = {
  MENTORING_APPLY: "멘토링 신청",
  MENTORING_CANCEL: "멘토링 취소",
};
