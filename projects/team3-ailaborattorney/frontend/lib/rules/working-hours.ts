import type { ContractData, UserInfo, Violation } from "./types";
import { STANDARD_WEEKLY_HOURS, STANDARD_DAILY_HOURS } from "./constants";

export function checkWorkingHours(c: ContractData, u: UserInfo): Violation | null {
  const weekly = u.weeklyHours ?? c.weeklyHours;
  if (weekly == null) return null;
  if (weekly > 52) {
    return {
      type: "working_hours_excess",
      title: "주 52시간 초과",
      risk: "high",
      message: `주 ${weekly}시간은 근로기준법상 한도(52시간)를 초과합니다.`,
      lawReference: "근로기준법 제53조",
      evidence: { weekly }
    };
  }
  if (weekly > STANDARD_WEEKLY_HOURS) {
    return {
      type: "overtime",
      title: "연장근로 발생",
      risk: "medium",
      message: `법정 주 ${STANDARD_WEEKLY_HOURS}시간을 초과하는 ${weekly - STANDARD_WEEKLY_HOURS}시간은 연장근로로 가산수당(1.5배) 대상입니다.`,
      lawReference: "근로기준법 제56조",
      evidence: { weekly, overtime: weekly - STANDARD_WEEKLY_HOURS }
    };
  }
  if (c.dailyHours != null && c.dailyHours > STANDARD_DAILY_HOURS) {
    return {
      type: "daily_overtime",
      title: "1일 8시간 초과",
      risk: "medium",
      message: `1일 ${c.dailyHours}시간은 법정기준 ${STANDARD_DAILY_HOURS}시간을 초과합니다.`,
      lawReference: "근로기준법 제50조",
      evidence: { dailyHours: c.dailyHours }
    };
  }
  return null;
}
