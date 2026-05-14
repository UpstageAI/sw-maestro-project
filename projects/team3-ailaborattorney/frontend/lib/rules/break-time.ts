import type { ContractData, UserInfo, Violation } from "./types";

export function checkBreakTime(c: ContractData, _u: UserInfo): Violation | null {
  if (c.dailyHours == null) return null;
  let required = 0;
  if (c.dailyHours >= 8) required = 60;
  else if (c.dailyHours >= 4) required = 30;
  if (required === 0) return null;
  const actual = c.breakMinutes ?? 0;
  if (actual >= required) return null;
  return {
    type: "break_time",
    title: "휴게시간 부족",
    risk: "medium",
    message: `1일 ${c.dailyHours}시간 근무 시 ${required}분 이상 휴게가 필요하나 계약서상 ${actual}분으로 명시되어 있습니다.`,
    lawReference: "근로기준법 제54조",
    evidence: { required, actual }
  };
}
