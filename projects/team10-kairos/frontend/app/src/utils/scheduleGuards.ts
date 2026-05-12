import type {
  ScheduleCandidate,
  ScheduleCreatePayload,
} from "../types/schedule";

export type MissingField = "title" | "start_at";

export function composeInput(originalText: string, answer: string): string {
  return `${originalText.trim()} 추가 정보: ${answer.trim()}`;
}

export function getMissingFields(candidate: ScheduleCandidate): MissingField[] {
  const missing: MissingField[] = [];
  if (!candidate.title?.trim()) {
    missing.push("title");
  }
  if (!isIsoDateTime(candidate.start_at)) {
    missing.push("start_at");
  }
  return missing;
}

export function getFollowUpQuestion(candidate: ScheduleCandidate): string {
  if (!isIsoDateTime(candidate.start_at)) {
    return "몇 월 며칠, 몇 시 일정인가요?";
  }
  if (!candidate.title?.trim()) {
    return "일정 이름을 어떻게 적을까요?";
  }
  return "추가로 필요한 정보를 알려주세요.";
}

export function isReadyToConfirm(candidate: ScheduleCandidate): boolean {
  return getMissingFields(candidate).length === 0;
}

export function buildSchedulePayload(
  candidate: ScheduleCandidate,
  originalText: string,
): ScheduleCreatePayload {
  if (!candidate.title?.trim() || !isIsoDateTime(candidate.start_at)) {
    throw new Error("필수 일정 정보가 부족합니다.");
  }

  return {
    title: candidate.title.trim(),
    start_at: candidate.start_at,
    end_at: candidate.end_at || null,
    location: candidate.location?.trim() || null,
    reminder_minutes: candidate.reminder_minutes ?? 30,
    original_text: originalText,
  };
}

export function reminderText(value: number | null | undefined): string {
  const minutes = value ?? 30;
  if (minutes === 0) {
    return "시작 시간";
  }
  if (minutes % 60 === 0) {
    return `${minutes / 60}시간 전`;
  }
  return `${minutes}분 전`;
}

export function isIsoDateTime(value: string | null | undefined): value is string {
  if (!value || !value.includes("T")) {
    return false;
  }
  const time = new Date(value).getTime();
  return Number.isFinite(time);
}
