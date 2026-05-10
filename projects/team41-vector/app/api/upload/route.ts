import { NextResponse } from 'next/server';
import Papa from 'papaparse';
import getDb from '@/lib/db';

const REQUIRED_HEADERS = ['date', 'category', 'merchant', 'amount'];

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get('file') as File | null;
    const userId = formData.get('userId') as string | null;

    if (!file || !userId) {
      return NextResponse.json(
        { error: 'file과 userId가 필요합니다.' },
        { status: 400 },
      );
    }

    const csvText = await file.text();
    const parsed = Papa.parse<Record<string, string>>(csvText, {
      header: true,
      skipEmptyLines: true,
    });

    // 헤더 검증
    const headers = parsed.meta.fields ?? [];
    const headersMatch =
      headers.length === REQUIRED_HEADERS.length &&
      REQUIRED_HEADERS.every((h, i) => headers[i] === h);

    if (!headersMatch) {
      return NextResponse.json(
        { error: 'CSV 헤더가 올바르지 않습니다. date,category,merchant,amount 형식이어야 합니다.' },
        { status: 400 },
      );
    }

    const db = getDb();

    // users 테이블에 없으면 기본값으로 INSERT
    const existingUser = db.prepare('SELECT id FROM users WHERE id = ?').get(userId);
    if (!existingUser) {
      db.prepare(
        'INSERT INTO users (id, name, monthly_income, current_savings, created_at) VALUES (?, ?, ?, ?, ?)',
      ).run(userId, '사용자', 2800000, 5000000, Date.now());
    }

    // 기존 transactions 삭제 후 새 데이터 삽입
    db.prepare('DELETE FROM transactions WHERE user_id = ?').run(userId);

    const insertStmt = db.prepare(
      'INSERT INTO transactions (user_id, date, category, merchant, amount) VALUES (?, ?, ?, ?, ?)',
    );

    let transactionCount = 0;
    let totalSpending = 0;
    const categoryTotals: Record<string, number> = {};
    let minDate = '';
    let maxDate = '';

    const insertAll = db.transaction((rows: Record<string, string>[]) => {
      for (const row of rows) {
        const amount = Number(row.amount);
        if (!row.date || isNaN(amount) || amount <= 0) continue;

        insertStmt.run(userId, row.date, row.category, row.merchant, amount);
        transactionCount++;
        totalSpending += amount;

        categoryTotals[row.category] = (categoryTotals[row.category] ?? 0) + amount;

        if (!minDate || row.date < minDate) minDate = row.date;
        if (!maxDate || row.date > maxDate) maxDate = row.date;
      }
    });

    insertAll(parsed.data);

    // topCategory 찾기
    let topCategory = '';
    let topAmount = 0;
    for (const [cat, total] of Object.entries(categoryTotals)) {
      if (total > topAmount) {
        topCategory = cat;
        topAmount = total;
      }
    }

    return NextResponse.json({
      userId,
      transactionCount,
      summary: {
        totalSpending,
        topCategory,
        period: { from: minDate, to: maxDate },
      },
    });
  } catch (error) {
    console.error('[upload] error:', error);
    return NextResponse.json(
      { error: '파일 처리 중 오류가 발생했습니다.' },
      { status: 500 },
    );
  }
}
