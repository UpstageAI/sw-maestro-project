import type { Schedule, ScheduleCandidate } from "../../../types/schedule";

export type FlowStatus =
  | "idle"
  | "analyzing"
  | "needsInput"
  | "confirming"
  | "saving"
  | "done"
  | "failed";

export const emptyCandidate: ScheduleCandidate = {
  title: null,
  start_at: null,
  end_at: null,
  location: null,
  reminder_minutes: null,
};

export const quickReplies = ["오전 10시", "오후 3시", "이번 주 토요일 오후 6시"];

export function normalizeCandidate(
  candidate: ScheduleCandidate,
): ScheduleCandidate {
  return {
    title: candidate.title,
    start_at: candidate.start_at,
    end_at: candidate.end_at,
    location: candidate.location,
    reminder_minutes:
      typeof candidate.reminder_minutes === "number"
        ? Math.max(0, candidate.reminder_minutes)
        : null,
  };
}

export function toCandidate(schedule: Schedule): ScheduleCandidate {
  return {
    title: schedule.title,
    start_at: schedule.start_at,
    end_at: schedule.end_at,
    location: schedule.location,
    reminder_minutes: schedule.reminder_minutes,
  };
}

export function newScheduleRunId() {
  return `schedule-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}
