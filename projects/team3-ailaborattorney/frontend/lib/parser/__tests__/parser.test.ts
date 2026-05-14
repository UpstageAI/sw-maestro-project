import assert from "node:assert/strict";
import { parseContract } from "../contract-parser";

const sample = `제4조 (근로시간) 1일 9시간(휴게 30분 포함), 주 5일 근무, 주 45시간
제5조 (휴게시간) 12:00 ~ 12:30 (30분)
제6조 (임금) 월 1,800,000원, 매월 25일 지급
제7조 (휴일) 매주 일요일을 주휴일로 한다.
제8조 (수습기간) 입사일로부터 3개월간 수습기간으로 하며, 수습기간 중 임금은 본 임금의 90%로 한다.
2025년 1월 1일부터 2025년 12월 31일까지`;

const r = parseContract(sample);
assert.equal(r.monthlyWage, 1800000);
assert.equal(r.weeklyHours, 45);
assert.equal(r.dailyHours, 9);
assert.equal(r.breakMinutes, 30);
assert.equal(r.weeklyRestDays, 1);
assert.equal(r.probationMonths, 3);
assert.equal(r.probationWageRate, 0.9);
assert.equal(r.startDate, "2025-01-01");
assert.equal(r.endDate, "2025-12-31");
console.log("parser tests passed");
