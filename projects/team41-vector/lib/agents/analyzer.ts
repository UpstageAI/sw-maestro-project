// ─── Analyzer ───
// 거래 내역(Transaction[])을 받아서 분석 결과(AnalysisResult)를 돌려주는 순수 함수 모음.
// LLM을 쓰지 않고 JS로만 계산하므로 빠르고 비용이 없다.
// 결과는 Coach(LLM)의 시스템 프롬프트에 주입된다.

import { Transaction, AnalysisResult, RiskPattern } from '@/lib/types';

// 메인 함수: 거래 배열 → 분석 결과
export function analyze(transactions: Transaction[]): AnalysisResult {
  // ── 기본 집계 ──
  let totalSpending = 0;
  const byCategory: Record<string, { count: number; total: number }> = {};
  const merchantMap: Record<string, { count: number; total: number }> = {};
  let minDate = '';
  let maxDate = '';

  for (const tx of transactions) {
    totalSpending += tx.amount;

    // 카테고리별 건수·합계
    if (!byCategory[tx.category]) byCategory[tx.category] = { count: 0, total: 0 };
    byCategory[tx.category].count += 1;
    byCategory[tx.category].total += tx.amount;

    // 가맹점별 건수·합계
    if (!merchantMap[tx.merchant]) merchantMap[tx.merchant] = { count: 0, total: 0 };
    merchantMap[tx.merchant].count += 1;
    merchantMap[tx.merchant].total += tx.amount;

    // 데이터 기간 계산 (문자열 비교로 min/max 추적)
    if (!minDate || tx.date < minDate) minDate = tx.date;
    if (!maxDate || tx.date > maxDate) maxDate = tx.date;
  }

  // 지출 합계 기준 상위 5개 가맹점
  const topMerchants = Object.entries(merchantMap)
    .map(([name, stats]) => ({ name, count: stats.count, total: stats.total }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 5);

  // ── 위험 패턴 탐지 (4종) ──
  const riskPatterns: RiskPattern[] = [];
  detectRecurringExcess(transactions, riskPatterns);   // 반복 과소비
  detectImpulse(transactions, riskPatterns);           // 충동구매
  detectUnusedSubscription(transactions, riskPatterns); // 미사용 구독
  detectLifestyleCreep(transactions, riskPatterns);     // 생활 수준 상승

  return {
    totalSpending,
    byCategory,
    riskPatterns,
    topMerchants,
    period: { from: minDate, to: maxDate },
  };
}

// ── 패턴 탐지 함수들 ──

// 반복 과소비: 배달 주 4회 이상 or 카페 하루 2회 이상
function detectRecurringExcess(transactions: Transaction[], patterns: RiskPattern[]): void {
  const deliveryByWeek: Record<string, Transaction[]> = {};
  const cafeByDay: Record<string, Transaction[]> = {};

  for (const tx of transactions) {
    if (tx.category === '배달') {
      const week = getWeekKey(tx.date);
      if (!deliveryByWeek[week]) deliveryByWeek[week] = [];
      deliveryByWeek[week].push(tx);
    }
    if (tx.category === '카페') {
      if (!cafeByDay[tx.date]) cafeByDay[tx.date] = [];
      cafeByDay[tx.date].push(tx);
    }
  }

  // 기준 초과 주차만 필터
  const excessDeliveryWeeks = Object.values(deliveryByWeek).filter(txs => txs.length >= 4);
  if (excessDeliveryWeeks.length > 0) {
    const totalAmount = excessDeliveryWeeks.reduce(
      (sum, txs) => sum + txs.reduce((s, t) => s + t.amount, 0), 0,
    );
    patterns.push({
      type: 'recurring_excess',
      description: `배달 주 4회 이상 사용 (${excessDeliveryWeeks.length}주 해당)`,
      amount: totalAmount,
      frequency: excessDeliveryWeeks.reduce((sum, txs) => sum + txs.length, 0),
    });
  }

  const excessCafeDays = Object.values(cafeByDay).filter(txs => txs.length >= 2);
  if (excessCafeDays.length > 0) {
    const totalAmount = excessCafeDays.reduce(
      (sum, txs) => sum + txs.reduce((s, t) => s + t.amount, 0), 0,
    );
    patterns.push({
      type: 'recurring_excess',
      description: `카페 하루 2회 이상 방문 (${excessCafeDays.length}일 해당)`,
      amount: totalAmount,
      frequency: excessCafeDays.reduce((sum, txs) => sum + txs.length, 0),
    });
  }
}

// 충동구매: 팝업스토어/쇼핑에서 단건 3만원 이상이 한 달에 3회 이상
function detectImpulse(transactions: Transaction[], patterns: RiskPattern[]): void {
  const impulseByMonth: Record<string, Transaction[]> = {};

  for (const tx of transactions) {
    if ((tx.category === '팝업스토어' || tx.category === '쇼핑') && tx.amount >= 30000) {
      const month = tx.date.slice(0, 7);
      if (!impulseByMonth[month]) impulseByMonth[month] = [];
      impulseByMonth[month].push(tx);
    }
  }

  for (const [month, txs] of Object.entries(impulseByMonth)) {
    if (txs.length >= 3) {
      patterns.push({
        type: 'impulse',
        description: `${month} 팝업스토어/쇼핑 충동소비 ${txs.length}회 (단건 3만원 이상)`,
        amount: txs.reduce((sum, t) => sum + t.amount, 0),
        frequency: txs.length,
      });
    }
  }
}

// 미사용 구독: 구독료 카테고리 거래 전체를 위험으로 표시
// (실사용 여부는 데이터만으로 판단 불가 → LLM이 사용자에게 확인 유도)
function detectUnusedSubscription(transactions: Transaction[], patterns: RiskPattern[]): void {
  const subscriptions = transactions.filter(tx => tx.category === '구독료');
  if (subscriptions.length === 0) return;

  patterns.push({
    type: 'unused_subscription',
    description: `구독 서비스 ${subscriptions.length}건 감지 — 실사용 여부 점검 필요`,
    amount: subscriptions.reduce((sum, t) => sum + t.amount, 0),
    frequency: subscriptions.length,
  });
}

// 라이프스타일 상승: 같은 카테고리 지출이 전월 대비 30% 이상 늘었을 때
// 데이터가 2개월 이상 있어야 비교 가능
function detectLifestyleCreep(transactions: Transaction[], patterns: RiskPattern[]): void {
  // 월별-카테고리별 합계 맵
  const monthCat: Record<string, Record<string, number>> = {};
  for (const tx of transactions) {
    const month = tx.date.slice(0, 7);
    if (!monthCat[month]) monthCat[month] = {};
    if (!monthCat[month][tx.category]) monthCat[month][tx.category] = 0;
    monthCat[month][tx.category] += tx.amount;
  }

  const months = Object.keys(monthCat).sort();
  if (months.length < 2) return;

  // 가장 최근 두 달만 비교
  const latestMonth = months[months.length - 1];
  const previousMonth = months[months.length - 2];
  const latestData = monthCat[latestMonth];
  const previousData = monthCat[previousMonth];

  for (const category of Object.keys(latestData)) {
    const prev = previousData[category];
    if (!prev || prev === 0) continue;

    const curr = latestData[category];
    const increase = (curr - prev) / prev;

    if (increase >= 0.3) {
      patterns.push({
        type: 'lifestyle_creep',
        description: `${category} 지출 ${latestMonth} 기준 전월 대비 ${Math.round(increase * 100)}% 증가 (${prev.toLocaleString()}원 → ${curr.toLocaleString()}원)`,
        amount: curr - prev,
        frequency: 1,
      });
    }
  }
}

// 날짜 문자열 → 그 주의 월요일 날짜 문자열 (주 단위 그룹핑 키로 사용)
function getWeekKey(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const dayOfWeek = d.getDay(); // 0=일, 1=월, ...
  const monday = new Date(d);
  const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // 월요일까지의 차이
  monday.setDate(d.getDate() + diff);
  return `${monday.getFullYear()}-${String(monday.getMonth() + 1).padStart(2, '0')}-${String(monday.getDate()).padStart(2, '0')}`;
}
