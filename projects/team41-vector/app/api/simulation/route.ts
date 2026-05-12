import { NextResponse } from 'next/server';
import getDb from '@/lib/db';
import { analyze } from '@/lib/agents/analyzer';
import { simulate } from '@/lib/agents/simulator';
import type { Transaction } from '@/lib/types';

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const userId = searchParams.get('userId');

    if (!userId) {
      return NextResponse.json({ error: 'userId가 필요합니다.' }, { status: 400 });
    }

    const db = getDb();

    // 사용자 정보 조회
    const user = db.prepare('SELECT monthly_income, current_savings FROM users WHERE id = ?').get(userId) as
      | { monthly_income: number; current_savings: number }
      | undefined;

    // query params로 오버라이드 가능
    const monthlyIncome = Number(searchParams.get('monthlyIncome')) || user?.monthly_income || 2800000;
    const currentSavings = Number(searchParams.get('currentSavings')) || user?.current_savings || 5000000;

    // 거래 데이터 조회
    const transactions = db
      .prepare('SELECT date, category, merchant, amount FROM transactions WHERE user_id = ?')
      .all(userId) as Transaction[];

    if (transactions.length === 0) {
      return NextResponse.json(
        { error: '거래 데이터가 없습니다. CSV를 먼저 업로드해주세요.' },
        { status: 404 },
      );
    }

    // Analyzer → Simulator
    const analysis = analyze(transactions);
    const simulationResult = simulate({
      monthlyIncome,
      totalSpending: analysis.totalSpending,
      currentSavings,
      riskPatternSavings: analysis.riskPatterns.reduce((s, p) => s + p.amount, 0),
    });

    return NextResponse.json(simulationResult);
  } catch (error) {
    console.error('[simulation] error:', error);
    return NextResponse.json(
      { error: '시뮬레이션 조회 중 오류가 발생했습니다.' },
      { status: 500 },
    );
  }
}
