import { useQuery } from "@tanstack/react-query";
import { apiUrl } from "./base";

export type ReportCategory = "테크" | "경제" | "정책" | "이슈";

export type DailyReportTimelineItem = {
  articleId: string;
  category: ReportCategory;
  timeLabel: string;
  title: string;
  sourceCount: number;
  summary?: string;
};

export type DailyReportFlowItem = {
  category: string;
  description: string;
};

export type DailyReportKeyword = {
  text: string;
  weight: number;
};

export type DailyReport = {
  date: string;
  updatedAt: string;
  briefing: {
    headline: string;
    summary: string;
  };
  timeline: DailyReportTimelineItem[];
  flow: DailyReportFlowItem[];
  keywords: DailyReportKeyword[];
};

type ReportErrorResponse = {
  code?: string;
  date?: string;
  message?: string;
};

export class DailyReportNotReadyError extends Error {
  constructor(
    readonly date: string,
    message = "아직 리포트가 준비되지 않았어요",
  ) {
    super(message);
    this.name = "DailyReportNotReadyError";
  }
}

export function dailyReportQueryKey(date: string) {
  return ["daily-report", date] as const;
}

export async function fetchDailyReport(date: string): Promise<DailyReport> {
  const response = await fetch(apiUrl(`/api/report/${date}`));

  if (response.status === 404) {
    const body = (await response.json().catch(() => null)) as ReportErrorResponse | null;
    throw new DailyReportNotReadyError(body?.date ?? date, body?.message);
  }

  if (!response.ok) {
    throw new Error("Failed to fetch daily report");
  }

  return response.json() as Promise<DailyReport>;
}

export function useDailyReport(date: string) {
  return useQuery({
    queryKey: dailyReportQueryKey(date),
    queryFn: () => fetchDailyReport(date),
  });
}
