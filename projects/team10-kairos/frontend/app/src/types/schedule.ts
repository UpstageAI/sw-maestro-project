export type ScheduleCandidate = {
  title: string | null;
  start_at: string | null;
  end_at: string | null;
  location: string | null;
  reminder_minutes: number | null;
};

export type AnalyzeScheduleResponse = {
  original_text: string;
  schedule: ScheduleCandidate;
  message: string;
};

export type ScheduleCreatePayload = {
  title: string;
  start_at: string;
  end_at?: string | null;
  location?: string | null;
  reminder_minutes: number;
  original_text?: string | null;
};

export type Schedule = {
  id: number;
  title: string;
  start_at: string;
  end_at: string | null;
  location: string | null;
  reminder_minutes: number;
  original_text?: string | null;
  status: string;
};
