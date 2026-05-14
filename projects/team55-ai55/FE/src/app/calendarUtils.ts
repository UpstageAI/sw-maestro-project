const CALENDAR_START_HOUR = 6;
const CALENDAR_END_HOUR = 24;
const CALENDAR_HOUR_HEIGHT = 40;

type CalendarLayoutEvent = {
  id: string;
  date: string;
  assigneeId: string | null;
  startTime: string;
  endTime: string;
  approved: boolean;
};

export function calendarHours() {
  return Array.from({ length: CALENDAR_END_HOUR - CALENDAR_START_HOUR }, (_, index) => CALENDAR_START_HOUR + index);
}

export function calendarGridHeight() {
  return (CALENDAR_END_HOUR - CALENDAR_START_HOUR) * CALENDAR_HOUR_HEIGHT;
}

export function calendarEventPosition(event: Pick<CalendarLayoutEvent, "startTime" | "endTime">) {
  const start = Math.max(CALENDAR_START_HOUR * 60, timeToMinutes(event.startTime));
  const end = Math.min(CALENDAR_END_HOUR * 60, timeToMinutes(event.endTime));
  const top = ((start - CALENDAR_START_HOUR * 60) / 60) * CALENDAR_HOUR_HEIGHT;
  const duration = Math.max(30, end - start);
  return {
    top,
    height: (duration / 60) * CALENDAR_HOUR_HEIGHT,
  };
}

export function calendarEventHasLocalConflict(event: CalendarLayoutEvent, events: CalendarLayoutEvent[]) {
  if (!event.assigneeId || event.endTime <= event.startTime) return false;
  const start = timeToMinutes(event.startTime);
  const end = timeToMinutes(event.endTime);
  return events.some((candidate) => {
    if (
      candidate.id === event.id ||
      !candidate.approved ||
      candidate.date !== event.date ||
      candidate.assigneeId !== event.assigneeId ||
      candidate.endTime <= candidate.startTime
    ) {
      return false;
    }
    return start < timeToMinutes(candidate.endTime) && end > timeToMinutes(candidate.startTime);
  });
}

function timeToMinutes(value: string) {
  const [hour, minute] = value.split(":").map((part) => Number(part));
  return (Number.isFinite(hour) ? hour : CALENDAR_START_HOUR) * 60 + (Number.isFinite(minute) ? minute : 0);
}
