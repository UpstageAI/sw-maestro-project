import type { Schedule } from "../types/schedule";

export type DateKey = `${number}-${number}-${number}`;

const TIMEZONE = process.env.EXPO_PUBLIC_TIMEZONE ?? "Asia/Seoul";
const koDate = new Intl.DateTimeFormat("ko-KR", {
  timeZone: TIMEZONE,
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "long",
});
const koTime = new Intl.DateTimeFormat("ko-KR", {
  timeZone: TIMEZONE,
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});

export function toDateKey(value: string | Date): DateKey {
  const date = value instanceof Date ? value : new Date(value);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const year = parts.find((part) => part.type === "year")?.value ?? "1970";
  const month = parts.find((part) => part.type === "month")?.value ?? "01";
  const day = parts.find((part) => part.type === "day")?.value ?? "01";
  return `${year}-${month}-${day}` as DateKey;
}

export function todayKey(): DateKey {
  return toDateKey(new Date());
}

export function formatDate(value: string): string {
  return koDate.format(new Date(value));
}

export function formatTime(value: string): string {
  return koTime.format(new Date(value));
}

export function formatTimeRange(schedule: Schedule): string {
  if (!schedule.end_at) {
    return formatTime(schedule.start_at);
  }
  return `${formatTime(schedule.start_at)} - ${formatTime(schedule.end_at)}`;
}

export function groupSchedulesByDate(
  schedules: Schedule[],
): Record<DateKey, Schedule[]> {
  return schedules.reduce<Record<DateKey, Schedule[]>>((groups, schedule) => {
    const key = toDateKey(schedule.start_at);
    groups[key] = [...(groups[key] ?? []), schedule].sort(
      (a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime(),
    );
    return groups;
  }, {});
}

export function keyToLocalDate(key: string): Date {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function toMonthKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(
    2,
    "0",
  )}`;
}

export function buildMonthCells(monthDate: Date): Array<{
  key: DateKey;
  day: number;
  inMonth: boolean;
}> {
  const first = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
  const cursor = new Date(first);
  cursor.setDate(first.getDate() - first.getDay());

  return Array.from({ length: 42 }, () => {
    const current = new Date(cursor);
    cursor.setDate(cursor.getDate() + 1);
    return {
      key: toDateKey(current),
      day: current.getDate(),
      inMonth: current.getMonth() === monthDate.getMonth(),
    };
  });
}

export function addMonths(date: Date, amount: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + amount, 1);
}
