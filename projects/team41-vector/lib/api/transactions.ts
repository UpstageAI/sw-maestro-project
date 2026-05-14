import type { Transaction } from '@/lib/types';

export async function getTransactions(userId: string): Promise<{
  transactions: Transaction[];
  stats: { total: number; byCategory: Record<string, number> };
}> {
  const res = await fetch(`/api/transactions?userId=${encodeURIComponent(userId)}`);
  if (!res.ok) throw new Error('거래 내역 조회에 실패했어요.');
  return res.json();
}
