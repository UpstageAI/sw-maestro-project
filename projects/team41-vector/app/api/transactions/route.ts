import { NextResponse } from 'next/server';
import getDb from '@/lib/db';

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const userId = searchParams.get('userId');

    if (!userId) {
      return NextResponse.json({ error: 'userId가 필요합니다.' }, { status: 400 });
    }

    const db = getDb();

    // 조건부 쿼리 빌드
    const conditions: string[] = ['user_id = ?'];
    const params: (string | number)[] = [userId];

    const category = searchParams.get('category');
    if (category) {
      conditions.push('category = ?');
      params.push(category);
    }

    const from = searchParams.get('from');
    if (from) {
      conditions.push('date >= ?');
      params.push(from);
    }

    const to = searchParams.get('to');
    if (to) {
      conditions.push('date <= ?');
      params.push(to);
    }

    const whereClause = conditions.join(' AND ');

    const transactions = db
      .prepare(`SELECT date, category, merchant, amount FROM transactions WHERE ${whereClause} ORDER BY date`)
      .all(...params);

    // byCategory: 독립 집계 (같은 WHERE 조건)
    const categoryStats = db
      .prepare(
        `SELECT category, SUM(amount) as total FROM transactions WHERE ${whereClause} GROUP BY category`,
      )
      .all(...params) as { category: string; total: number }[];

    const byCategory: Record<string, number> = {};
    let total = 0;
    for (const row of categoryStats) {
      byCategory[row.category] = row.total;
      total += row.total;
    }

    return NextResponse.json({
      transactions,
      stats: {
        total,
        byCategory,
      },
    });
  } catch (error) {
    console.error('[transactions] error:', error);
    return NextResponse.json(
      { error: '거래 내역 조회 중 오류가 발생했습니다.' },
      { status: 500 },
    );
  }
}
