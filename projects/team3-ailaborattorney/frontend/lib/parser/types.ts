// rule-engine의 ContractData와 호환되는 평면 구조 (별도 정의, 의존 없음)
export interface ParsedContract {
  monthlyWage?: number;
  hourlyWage?: number;
  weeklyHours?: number;
  dailyHours?: number;
  breakMinutes?: number;
  weeklyRestDays?: number;
  probationMonths?: number;
  probationWageRate?: number;
  contractType?: "permanent" | "fixed_term" | "part_time" | "daily" | "unknown";
  startDate?: string;
  endDate?: string;
  rawText?: string;
}
