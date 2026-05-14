const SEOUL_TIME_ZONE = "Asia/Seoul";

type SeoulDateTimeParts = {
  year: string;
  month: string;
  day: string;
  hour: string;
  minute: string;
};

const seoulDateTimeFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: SEOUL_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function getSeoulDateTimeParts(value: string): SeoulDateTimeParts | null {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const parts = new Map(
    seoulDateTimeFormatter
      .formatToParts(date)
      .map((part) => [part.type, part.value]),
  );
  const year = parts.get("year");
  const month = parts.get("month");
  const day = parts.get("day");
  const hour = parts.get("hour");
  const minute = parts.get("minute");

  if (!year || !month || !day || !hour || !minute) {
    return null;
  }

  return {
    year,
    month,
    day,
    hour: hour === "24" ? "00" : hour,
    minute,
  };
}

export function formatSeoulTime(value: string) {
  const parts = getSeoulDateTimeParts(value);

  return parts ? `${parts.hour}:${parts.minute}` : value;
}

export function formatSeoulDate(value: string) {
  const parts = getSeoulDateTimeParts(value);

  return parts ? `${parts.year}.${parts.month}.${parts.day}` : value;
}
