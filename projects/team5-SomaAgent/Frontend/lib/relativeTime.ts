// 미래 시각이 사실상 시계 차이(서버↔클라이언트) 때문일 때를 흡수하기 위한 허용 범위.
// 60초 이내 미래는 "방금 전" 으로 그대로 처리하고, 그보다 더 미래는 "예정" 처리한다.
const CLOCK_SKEW_TOLERANCE_MS = 60_000;

export function formatRelativeTime(
  iso: string | null | undefined,
  now: Date = new Date(),
): string {
  if (!iso) return "기록 없음";

  const target = new Date(iso);
  const diffMs = now.getTime() - target.getTime();
  if (Number.isNaN(diffMs)) return "기록 없음";

  // 미래(음수)이지만 클럭 스큐 범위 안이면 "방금 전" 으로 흡수.
  if (diffMs < -CLOCK_SKEW_TOLERANCE_MS) return "예정";
  if (diffMs < 60_000) return "방금 전";

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes}분 전`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}일 전`;

  return target.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function formatAbsoluteTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// 멘토링 카드 등에서 사용할 일정 표시 (예: "2026년 5월 8일 (목) · 14:00 – 15:30").
// 순수 함수로 두어 컴포넌트 외부에서 재사용 가능.
export function formatMentoringSchedule(
  start: string,
  end?: string,
): string {
  const startDate = new Date(start);
  if (Number.isNaN(startDate.getTime())) return start;

  const date = startDate.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  });
  const startTime = startDate.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  if (!end) return `${date} ${startTime}`;

  const endDate = new Date(end);
  if (Number.isNaN(endDate.getTime())) return `${date} ${startTime}`;

  const endTime = endDate.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${date} · ${startTime} – ${endTime}`;
}
