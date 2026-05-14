import type { ContractData, UserInfo, RuleResult, Violation } from "./types";
import { checkMinWage } from "./min-wage";
import { checkWorkingHours } from "./working-hours";
import { checkBreakTime } from "./break-time";
import { checkWeeklyRest } from "./weekly-rest";

export * from "./types";
export * from "./constants";

export function runRules(contract: ContractData, user: UserInfo = {}): RuleResult {
  const checks: Array<[string, (c: ContractData, u: UserInfo) => Violation | null]> = [
    ["min_wage", checkMinWage],
    ["working_hours", checkWorkingHours],
    ["break_time", checkBreakTime],
    ["weekly_rest", checkWeeklyRest],
  ];
  const violations: Violation[] = [];
  const checkedRules: string[] = [];
  for (const [name, fn] of checks) {
    checkedRules.push(name);
    const v = fn(contract, user);
    if (v) violations.push(v);
  }
  return { violations, checkedRules };
}
