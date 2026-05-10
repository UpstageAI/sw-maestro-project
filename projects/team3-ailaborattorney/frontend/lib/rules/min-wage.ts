import type { ContractData, UserInfo, Violation } from "./types";
import { MIN_HOURLY_WAGE_2025 } from "./constants";

// 시급 환산: hourlyWage 우선, 없으면 monthlyWage / (weeklyHours * 4.345)
export function checkMinWage(c: ContractData, _u: UserInfo): Violation | null {
  let hourly = c.hourlyWage;
  if (hourly == null && c.monthlyWage && c.weeklyHours) {
    const monthlyHours = c.weeklyHours * 4.345;
    if (monthlyHours > 0) hourly = c.monthlyWage / monthlyHours;
  }
  if (hourly == null) return null;
  if (hourly >= MIN_HOURLY_WAGE_2025) return null;
  return {
    type: "min_wage",
    title: "최저임금 미달 가능성",
    risk: "high",
    message: `환산 시급 ${Math.round(hourly).toLocaleString()}원이 2025년 최저임금 ${MIN_HOURLY_WAGE_2025.toLocaleString()}원보다 낮습니다.`,
    lawReference: "최저임금법 제6조",
    evidence: { computedHourly: Math.round(hourly), threshold: MIN_HOURLY_WAGE_2025 }
  };
}
