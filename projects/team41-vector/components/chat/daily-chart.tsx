'use client';

// ─── DailyChart ───
// 사용자가 "소비 그래프 보여줘"라고 하면 Coach가 get_daily_spending 툴을 호출하고,
// 그 결과로 이 컴포넌트가 채팅 메시지 바로 아래에 렌더링된다.
//
// 구성:
// - X축: 날짜 (1일, 2일, ...)
// - Y축: 금액 (천 단위 축약)
// - 카테고리별 얇은 색상 선 + 총합 굵은 짙은 선

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { DailySpendingData } from '@/lib/types';

type Props = { data: DailySpendingData };

// 카테고리 선 색상 팔레트 (순서대로 할당, 8개 순환)
const PALETTE = [
  '#7c3aed', '#f59e0b', '#10b981', '#ef4444',
  '#3b82f6', '#ec4899', '#14b8a6', '#f97316',
];

// Y축·툴팁 금액 포맷: 10,000원 이상은 "N천원"으로 축약
function formatWon(value: number) {
  if (value >= 10000) return `${Math.round(value / 1000)}천`;
  return `${value}`;
}

export function DailyChart({ data }: Props) {
  const { month, points, categories } = data;

  // X축 레이블: "2026-05-03" → "3일"
  const chartData = points.map((p) => ({
    ...p,
    label: `${parseInt(p.date.slice(8), 10)}일`,
  }));

  return (
    <div
      className="my-2 rounded-xl bg-white/60 p-4 ring-1 ring-[var(--border-soft)]"
      style={{ height: 260 }}
    >
      {/* 헤더: 조회 월 표시 */}
      <p className="mb-2 text-xs font-semibold text-[var(--ink-500)]">
        {month} 일별 소비
      </p>

      {/* height="85%": 헤더 텍스트 공간(15%)를 빼고 차트가 채운다 */}
      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={chartData} margin={{ left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis dataKey="label" fontSize={11} />
          <YAxis tickFormatter={formatWon} fontSize={11} width={46} />
          <Tooltip
            formatter={(v, name) =>
              [`${Number(v).toLocaleString()}원`, name as string]
            }
          />
          <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />

          {/* 카테고리별 선: PALETTE 색상 순서대로 */}
          {categories.map((cat, i) => (
            <Line
              key={cat}
              type="monotone"
              dataKey={cat}
              stroke={PALETTE[i % PALETTE.length]}
              strokeWidth={1.5}
              dot={false}       // 점 제거 → 선만 깔끔하게
              connectNulls      // 데이터 없는 날짜는 선으로 이어줌
            />
          ))}

          {/* 총합 선: 굵고 짙게 → 한눈에 전체 추이 파악 */}
          <Line
            type="monotone"
            dataKey="total"
            name="총합"
            stroke="#1e1b4b"
            strokeWidth={2.5}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
