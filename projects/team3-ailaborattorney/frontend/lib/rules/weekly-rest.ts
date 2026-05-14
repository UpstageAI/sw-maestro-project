import type { ContractData, UserInfo, Violation } from "./types";
import { PART_TIME_THRESHOLD_HOURS } from "./constants";

// 주휴일/주휴수당: 주15시간 이상 근로자는 1일 유급휴일
export function checkWeeklyRest(c: ContractData, u: UserInfo): Violation | null {
  const weekly = u.weeklyHours ?? c.weeklyHours;
  if (weekly == null) return null;
  if (weekly < PART_TIME_THRESHOLD_HOURS) {
    return {
      type: "short_time_worker",
      title: "초단시간 근로자",
      risk: "low",
      message: `주 ${weekly}시간(15시간 미만)은 초단시간 근로자로, 주휴수당·연차·퇴직금이 적용되지 않을 수 있습니다.`,
      lawReference: "근로기준법 제18조 제3항",
      evidence: { weekly }
    };
  }
  if ((c.weeklyRestDays ?? 0) < 1) {
    return {
      type: "weekly_rest",
      title: "주휴일 미명시",
      risk: "medium",
      message: "주 15시간 이상 근로자는 1주 1회 이상 유급 주휴일이 보장되어야 합니다.",
      lawReference: "근로기준법 제55조",
      evidence: { weeklyRestDays: c.weeklyRestDays ?? 0 }
    };
  }
  return null;
}
