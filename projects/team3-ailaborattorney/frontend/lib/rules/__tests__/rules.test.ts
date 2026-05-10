import assert from "node:assert/strict";
import { runRules } from "../index";

// 최저임금 미달
{
  const r = runRules({ hourlyWage: 9000, weeklyHours: 40 });
  assert.ok(r.violations.some(v => v.type === "min_wage"));
}
// 최저임금 통과
{
  const r = runRules({ hourlyWage: 12000, weeklyHours: 40 });
  assert.ok(!r.violations.some(v => v.type === "min_wage"));
}
// 연장근로
{
  const r = runRules({ weeklyHours: 50, hourlyWage: 12000 });
  assert.ok(r.violations.some(v => v.type === "overtime"));
}
// 휴게시간 부족
{
  const r = runRules({ dailyHours: 9, breakMinutes: 30, hourlyWage: 12000, weeklyHours: 40 });
  assert.ok(r.violations.some(v => v.type === "break_time"));
}
// 초단시간
{
  const r = runRules({ weeklyHours: 12, hourlyWage: 12000 });
  assert.ok(r.violations.some(v => v.type === "short_time_worker"));
}
console.log("rule-engine tests passed");
