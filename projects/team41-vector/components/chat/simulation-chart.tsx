'use client';

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
import type { SimulationResult } from '@/lib/types';

type Props = { data: SimulationResult };

// Y축·툴팁 레이블: 원 → 만원 단위로 축약 (ex. 5000000 → "500만")
function formatWon(value: number) {
  return `${Math.round(value / 10000)}만`;
}

// ─── SimulationChart ───
// Simulator가 계산한 1/3/5년 자산 예측을 라인 차트로 표시.
// 회색(현재 패턴) vs 보라(개선 패턴) 두 줄을 비교.
// simulator.ts의 SimulationResult 구조:
//   currentPattern.projections: [{ year: 1, assets }, { year: 3, assets }, { year: 5, assets }]
//   optimizedPattern.projections: 동일 구조
export function SimulationChart({ data }: Props) {
  // Recharts용 데이터 포맷으로 변환
  // currentPattern과 optimizedPattern의 같은 인덱스(연도)를 한 객체로 합침
  const chartData = data.currentPattern.projections.map((cp, i) => ({
    year: `${cp.year}년`,
    현재: cp.assets,
    개선: data.optimizedPattern.projections[i]?.assets ?? 0,
  }));

  return (
    // height 고정(200px): ResponsiveContainer가 부모 height를 기준으로 잡으므로
    // 부모에 height가 없으면 0이 되어 차트가 안 그려짐
    <div className="my-2 rounded-xl bg-white/60 p-3" style={{ height: 200 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis dataKey="year" fontSize={12} />
          {/* width={50}: 만원 단위 레이블이 잘리지 않도록 여백 확보 */}
          <YAxis tickFormatter={formatWon} fontSize={11} width={50} />
          <Tooltip formatter={(v) => formatWon(Number(v))} />
          <Legend />
          {/* 현재 패턴: 회색 */}
          <Line
            type="monotone"
            dataKey="현재"
            stroke="#a5a2b6"
            strokeWidth={2}
            dot={{ r: 4 }}
          />
          {/* 개선 패턴: 보라색 */}
          <Line
            type="monotone"
            dataKey="개선"
            stroke="#5b21b6"
            strokeWidth={2}
            dot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
