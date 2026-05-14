export type RiskLevel = "low" | "medium" | "high";

export interface ContractData {
  // 파서가 채워주는 구조화된 계약서 데이터
  monthlyWage?: number;       // 월급 (원)
  hourlyWage?: number;        // 시급 (원)
  weeklyHours?: number;       // 주당 근로시간
  dailyHours?: number;        // 1일 근로시간
  breakMinutes?: number;      // 1일 휴게시간(분)
  weeklyRestDays?: number;    // 주휴일 수
  probationMonths?: number;   // 수습 개월
  probationWageRate?: number; // 수습 급여율 (예: 0.9)
  contractType?: "permanent" | "fixed_term" | "part_time" | "daily" | "unknown";
  startDate?: string;
  endDate?: string;
  rawText?: string;
}

export interface UserInfo {
  weeklyHours?: number;       // 사용자가 직접 입력한 실제 주당 근로시간
  age?: number;
}

export interface Violation {
  type: string;               // e.g. "min_wage", "break_time"
  title: string;              // 한글 제목
  risk: RiskLevel;
  message: string;            // 위반 가능성 설명
  lawReference?: string;      // 근거 법령
  evidence?: Record<string, unknown>; // 계산 근거 데이터
}

export interface RuleResult {
  violations: Violation[];
  checkedRules: string[];     // 검사한 룰 type 목록
}
