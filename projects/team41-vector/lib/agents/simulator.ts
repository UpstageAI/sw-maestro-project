// ─── Simulator ───
// 현재 소비 패턴과 개선 패턴으로 1·3·5년 후 자산을 계산해 비교한다.
// LLM 없이 순수 JS 수식으로만 동작. Analyzer 결과를 받아서 Coach에 같이 넘긴다.

import { SimulationResult } from '@/lib/types';

export function simulate(params: {
  monthlyIncome: number;      // 월 수입 (원)
  totalSpending: number;      // 이번 달 총 지출 (원) — Analyzer.totalSpending
  currentSavings: number;     // 현재 보유 저축액 (원)
  riskPatternSavings: number; // 위험 패턴을 없앴을 때 절약 가능한 금액 (원) — Analyzer.riskPatterns 합계
  annualReturn?: number;      // 연 수익률 (기본 3.5% = 예금 기준 보수적 추정)
}): SimulationResult {
  const r = params.annualReturn ?? 0.035;
  const years = [1, 3, 5]; // 예측 시점

  // 현재 패턴: 지금처럼 쓰면 매달 이만큼 남는다
  const currentMonthlySaving = params.monthlyIncome - params.totalSpending;

  // 개선 패턴: 위험 패턴 금액을 아끼면 저축이 이만큼 더 늘어난다
  const optimizedMonthlySaving = currentMonthlySaving + params.riskPatternSavings;

  return {
    currentPattern: {
      monthlySaving: currentMonthlySaving,
      projections: years.map(n => ({
        year: n,
        assets: calcAssets(params.currentSavings, currentMonthlySaving, r, n),
      })),
    },
    optimizedPattern: {
      monthlySaving: optimizedMonthlySaving,
      projections: years.map(n => ({
        year: n,
        assets: calcAssets(params.currentSavings, optimizedMonthlySaving, r, n),
      })),
    },
  };
}

// n년 후 자산 계산 (복리)
// = 현재 저축의 복리 성장 + 매달 적립하는 돈의 복리 성장
//
// 현재 저축 성장:  currentSavings × (1 + r)^n
// 월 적립 성장:    monthlySaving × ((1 + r/12)^(12n) - 1) / (r/12)
//   → 매달 같은 금액을 넣는 적금의 만기 금액 공식 (연금 미래가치)
function calcAssets(
  currentSavings: number,
  monthlySaving: number,
  r: number,
  n: number,
): number {
  const monthlyRate = r / 12;

  const savingsGrowth = currentSavings * Math.pow(1 + r, n);

  // monthlyRate가 0이면 나눗셈 불가 → 단순 합산
  const annuityGrowth = monthlyRate === 0
    ? monthlySaving * 12 * n
    : monthlySaving * (Math.pow(1 + monthlyRate, 12 * n) - 1) / monthlyRate;

  return Math.round(savingsGrowth + annuityGrowth);
}
