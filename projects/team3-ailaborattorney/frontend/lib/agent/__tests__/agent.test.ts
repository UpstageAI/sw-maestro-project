import assert from "node:assert/strict";
import { analyzeMock, qaMock } from "../mock";

async function main() {
  const a = await analyzeMock({
    contract_data: { monthlyWage: 1800000, weeklyHours: 45 },
    rule_result: { violations: [{ type: "min_wage", title: "최저임금 미달 가능성", risk: "high", message: "..." }] },
  });
  assert.equal(a.source, "mock");
  assert.equal(a.items.length >= 1, true);
  assert.equal(a.items[0].risk_level, "high");

  const q = await qaMock({ question: "수습기간 동안 최저임금 90%만 받아도 되나요?" });
  assert.equal(q.source, "mock");
  assert.ok(q.answer.length > 0);
  console.log("agent tests passed");
}

main();
